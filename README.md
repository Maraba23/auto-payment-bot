
# Discord Bot com Pagamento Automático via Pix

Este projeto é um bot de Discord que implementa pagamentos automáticos via Pix utilizando a API do Mercado Pago. Ele permite que usuários façam pagamentos diretamente pelo Discord e recebe notificações sobre os pagamentos.

## Funcionalidades

- Comandos de pagamento via Pix
- Notificações automáticas de pagamentos
- Integração com a API do Mercado Pago

## Pré-requisitos

- Python 3.8+
- Conta de desenvolvedor no Mercado Pago
- Token de acesso da API do Mercado Pago

## Configuração

1. **Clone o repositório:**

   ```bash
   git clone https://github.com/Maraba23/auto-payment-bot.git
   cd auto-payment-bot
   ```

2. **Instale as dependências:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configuração do Bot do Discord:**

   Você precisa substituir as variáveis `TOKEN`, `APPLICATION_ID` e `OWNERS` no código pelo token do seu próprio bot, o application ID do seu próprio bot e o ID do dono do bot, respectivamente.

   ```json
   {
   "prefix": "w!",
   "token": "Seu Token Aqui",
   "permissions": "8",
   "application_id": "Seu Aplication ID aqui",
   "sync_commands_globally": false,
   "owners": [
      Os IDs dos discords que sao os owners,
      ]
   }

   ```

4. **Arquivo `.env`:**

   Crie um arquivo `.env` na raiz do projeto e adicione a chave de acesso do Mercado Pago:

   ```
   MP_ACCESS_TOKEN=SEU_TOKEN_DE_ACESSO_MERCADO_PAGO
   ```

5. **Inicialize o bot:**

   ```bash
   python bot.py
   ```

## Uso

Para utilizar o bot, siga as instruções dos comandos dentro do Discord. O bot fornecerá comandos para iniciar o processo de pagamento via Pix e notificará automaticamente quando um pagamento for confirmado.

