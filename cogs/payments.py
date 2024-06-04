import discord
import requests
import json
import sqlite3
import qrcode

from discord.ext import commands, tasks
from discord.ext.commands import Context
from dotenv import load_dotenv
import os

load_dotenv()

# Setup SQLite
conn = sqlite3.connect('products.db')
c = conn.cursor()

# Create tables if they don't exist
c.execute('''CREATE TABLE IF NOT EXISTS products
             (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, identifier TEXT UNIQUE, price REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS stock
             (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, key TEXT, FOREIGN KEY(product_id) REFERENCES products(id))''')
c.execute('''CREATE TABLE IF NOT EXISTS payments
             (id INTEGER PRIMARY KEY AUTOINCREMENT, payment_id TEXT, status TEXT, channel_id INTEGER, product_id INTEGER)''')
conn.commit()

mp_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
mp_USER_ID = os.getenv("MP_USER_ID")
mp_EXTERNAL_ID = os.getenv("MP_EXTERNAL_ID")
mp_EXTERNAL_POS_ID = os.getenv("MP_EXTERNAL_POS_ID")

class Payments(commands.Cog, name="payments"):
    def __init__(self, bot):
        self.bot = bot
        self.check_payments.start()
        print("Started check_payments task.")

    @commands.hybrid_command(
        name="add-product",
        description="Adicionar um produto ao banco de dados"
    )
    @commands.has_permissions(administrator=True)
    async def add_product(self, ctx: Context, identifier: str, price: float, *, name: str) -> None:
        c.execute("INSERT INTO products (name, identifier, price) VALUES (?, ?, ?)", (name, identifier, price))
        conn.commit()
        await ctx.send(f"✅ **Produto Adicionado com Sucesso!**\n\n🔹 **Nome:** {name}\n🔹 **Identificador:** {identifier}\n🔹 **Preço:** R${price:.2f}")

    @commands.hybrid_command(
        name="remove-product",
        description="Remover um produto do banco de dados"
    )
    @commands.has_permissions(administrator=True)
    async def remove_product(self, ctx: Context, identifier: str) -> None:
        c.execute("DELETE FROM products WHERE identifier = ?", (identifier,))
        c.execute("DELETE FROM stock WHERE product_id IN (SELECT id FROM products WHERE identifier = ?)", (identifier,))
        conn.commit()
        await ctx.send(f"🗑️ **Produto Removido com Sucesso!**\n\n🔹 **Identificador:** {identifier}")

    @commands.hybrid_command(
        name="add-stock",
        description="Adicionar chaves de estoque para um produto"
    )
    @commands.has_permissions(administrator=True)
    async def add_stock(self, ctx: Context, identifier: str, *, keys: str) -> None:
        c.execute("SELECT id FROM products WHERE identifier = ?", (identifier,))
        product_id = c.fetchone()
        if product_id:
            product_id = product_id[0]
            for key in keys.split():
                c.execute("INSERT INTO stock (product_id, key) VALUES (?, ?)", (product_id, key))
            conn.commit()
            await ctx.send(f"📦 **Estoque Adicionado!**\n\n🔹 **Produto:** {identifier}\n🔹 **Chaves:** {keys}")
        else:
            await ctx.send(f"❌ **Erro:** Produto com identificador {identifier} não encontrado.")

    @commands.hybrid_command(
        name="list-products",
        description="Listar todos os produtos com estoque"
    )
    @commands.has_permissions(administrator=True)
    async def list_products(self, ctx: Context) -> None:
        c.execute("SELECT p.id, p.name, p.identifier, p.price, COUNT(s.id) as stock FROM products p LEFT JOIN stock s ON p.id = s.product_id GROUP BY p.id")
        products = c.fetchall()
        if not products:
            await ctx.send("🔍 **Nenhum produto encontrado.**")
            return
        
        embed = discord.Embed(title="📋 Lista de Produtos", description="Clique no botão abaixo e selecione o produto que deseja comprar, o bot vai criar um checkout para você",  color=0x5865F2)
        options = []
        for product in products:
            product_id, name, identifier, price, stock = product
            options.append(discord.SelectOption(label=f"{name}", description=f"💵 Valor: R${price:.2f} - 📦 Estoque: {stock}", value=identifier))

        select = discord.ui.Select(placeholder="Escolha um produto...", options=options)

        async def select_callback(interaction: discord.Interaction):
            selected_identifier = select.values[0]
            await self.create_checkout_channel(interaction.guild, interaction.user, selected_identifier)
            await interaction.response.send_message("📥 **Canal de checkout criado!**", ephemeral=True)

        select.callback = select_callback

        view = discord.ui.View()
        view.add_item(select)
        
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(
        name="list-all-products",
        description="Listar todos os produtos e seus IDs"
    )
    @commands.has_permissions(administrator=True)
    async def list_all_products(self, ctx: Context) -> None:
        c.execute("SELECT id, name, identifier FROM products")
        products = c.fetchall()
        if not products:
            await ctx.send("🔍 **Nenhum produto encontrado.**")
            return
        
        product_list = "\n".join([f"**ID:** {product[0]}, **Nome:** {product[1]}, **Identificador:** {product[2]}" for product in products])
        await ctx.send(f"📋 **Lista de Produtos:**\n{product_list}")

    async def create_checkout_channel(self, guild, user, identifier):
        # Verificar estoque do produto
        c.execute("SELECT COUNT(*) FROM stock WHERE product_id = (SELECT id FROM products WHERE identifier = ?)", (identifier,))
        stock_count = c.fetchone()[0]

        if stock_count == 0:
            await user.send(f"❌ **Desculpe, o produto {identifier} está fora de estoque.**")
            return

        # Criar o canal de checkout
        channel_name = f"checkout-{user.name}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        for role in guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(channel_name, overwrites=overwrites)

        # Gerar QR code e enviar no canal
        print(f"Creating QR code for {identifier}")
        await self.send_qrcode(channel, identifier)

    async def send_qrcode(self, channel, identifier):
        try:
            c.execute("SELECT id, name, price FROM products WHERE identifier = ?", (identifier,))
            product = c.fetchone()
            if not product:
                await channel.send("❌ **Erro:** Produto não encontrado.")
                return
            
            product_id, name, price = product
            print(f"Generating QR code for product: {name}, price: {price}")

            url = f"https://api.mercadopago.com/v1/payments"
            headers = {
                "Authorization": f"Bearer {mp_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            }

            data = {
                "additional_info": {
                    "items": [
                        {
                            "id": identifier,
                            "title": name,
                            "description": name,
                            "quantity": 1,
                            "unit_price": price,
                        }
                    ]
                },
                "payer": {
                    "email": "brizzer22@gmail.com"
                },
                "payment_method_id": "pix",
                "transaction_amount": price,
            }

            response = requests.post(url, headers=headers, data=json.dumps(data))
            response_json = response.json()
            qr_code = response_json["point_of_interaction"]["transaction_data"]["qr_code"]
            payment_id = response_json["id"]

            if not qr_code or not payment_id:
                print(f"Failed to generate QR code: {response_json}")
                await channel.send("❌ **Falha ao gerar o código QR.**")
                return

            # Salvar informações do pagamento no banco de dados
            c.execute("INSERT INTO payments (payment_id, status, channel_id, product_id) VALUES (?, ?, ?, ?)", (payment_id, "pending", channel.id, product_id))
            conn.commit()

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_code)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            img.save("qrcode.png")

            file = discord.File("qrcode.png", filename="qrcode.png")
            embed = discord.Embed(title="📲 Escaneie para Pagar", description=f"Escaneie este código QR para completar sua compra de **{name}**.", color=0x5865F2)
            embed.set_image(url="attachment://qrcode.png")
            await channel.send(embed=embed, file=file)
        except Exception as e:
            print(f"Error in send_qrcode: {e}")
            await channel.send("❌ **Ocorreu um erro ao gerar o código QR.**")

    @tasks.loop(minutes=1)
    async def check_payments(self):
        try:
            c.execute("SELECT payment_id, channel_id, product_id FROM payments WHERE status = 'pending'")
            pending_payments = c.fetchall()
            print(f"Checking {len(pending_payments)} pending payments...")
            for payment_id, channel_id, product_id in pending_payments:
                url = f"https://api.mercadopago.com/v1/payments/{payment_id}?access_token={mp_ACCESS_TOKEN}"
                # headers = {
                #     "Authorization": f"Bearer {mp_ACCESS_TOKEN}"
                # }
                print(f"Checking payment: {payment_id}")
                response = requests.get(url)
                print(response.json())
                if response.status_code == 200:
                    payment_data = response.json()
                    if payment_data['status'] == 'approved':
                        c.execute("UPDATE payments SET status = 'approved' WHERE payment_id = ?", (payment_id,))
                        conn.commit()

                        # Retrieve a key for the product
                        c.execute("SELECT key FROM stock WHERE product_id = ? LIMIT 1", (product_id,))
                        product_key = c.fetchone()
                        print(f"Product key: {product_key}")
                        if product_key:
                            product_key = product_key[0]
                            c.execute("DELETE FROM stock WHERE key = ?", (product_key,))
                            conn.commit()

                            channel = self.bot.get_channel(channel_id)
                            if channel:
                                await channel.send(f"✅ **Pagamento Aprovado!**\n\nObrigado pela compra! Aqui está sua chave de produto: `{product_key}`")
                        else:
                            channel = self.bot.get_channel(channel_id)
                            if channel:
                                await channel.send("✅ **Pagamento Aprovado!**\n\nNo entanto, não há nenhuma chave de produto disponível no momento.")
        except Exception as e:
            print(f"Error in check_payments: {e}")

async def setup(bot):
    await bot.add_cog(Payments(bot))
