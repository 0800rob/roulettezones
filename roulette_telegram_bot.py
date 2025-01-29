import asyncio
from playwright.async_api import async_playwright
import requests
from collections import defaultdict, deque

# Configurações do Telegram
TOKEN = "TOKEN" #Token criado pelo BotFather
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"
chat_ids = set()
last_update_id = None

# Restrição de acesso: Substitua pelo seu próprio chat_id
ALLOWED_CHAT_IDS = {}  # Substitua pelo seu chat_id

def send_telegram_message(chat_id, message):
    """Envia uma mensagem para o chat especificado."""
    if chat_id not in ALLOWED_CHAT_IDS:
        return
    
    message = message.encode('utf-16', 'surrogatepass').decode('utf-16')
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Error sending message: {e}")

def get_updates():
    """Obtém atualizações das mensagens enviadas ao bot."""
    global last_update_id
    url = f"{BASE_URL}/getUpdates"
    try:
        payload = {"offset": last_update_id + 1} if last_update_id else {}
        response = requests.get(url, params=payload)
        if response.status_code == 200:
            updates = response.json().get("result", [])
            for update in updates:
                update_id = update.get("update_id")
                if last_update_id is None or update_id > last_update_id:
                    last_update_id = update_id
                    
                    message = update.get("message", {})
                    chat_id = message.get("chat", {}).get("id")
                    text = message.get("text", "").strip().lower()
                    
                    if chat_id not in ALLOWED_CHAT_IDS:
                        continue
                    
                    if text == "/start" and chat_id not in chat_ids:
                        chat_ids.add(chat_id)
                        send_telegram_message(chat_id, "🤖 Bot ativado! Você receberá notificações.")
    except Exception as e:
        print(f"Erro ao obter atualizações: {e}")

async def update_chats():
    """Atualiza os IDs dos chats em um intervalo fixo."""
    while True:
        get_updates()
        await asyncio.sleep(5)

async def resultado(page):
    """Obtém os últimos números da roleta."""
    results = await page.eval_on_selector_all(
        "#q-app .roulette-number",
        'elements => elements.map(element => element.innerText.trim())'
    )
    return [int(result.split('\n')[0]) for result in results if result.split('\n')[0].isdigit()][:10]

async def monitorar_roletas(roletas):
    """Monitora roletas e coleta os últimos números."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        pages = {}
        
        for id_roleta in roletas:
            pages[id_roleta] = await context.new_page()
            await pages[id_roleta].goto(f"https://gamblingcounting.com/{id_roleta}")
        
        while True:
            for id_roleta, page in pages.items():
                try:
                    results = await resultado(page)
                    if results:
                        message = f"🎰 *Roleta:* {id_roleta}\n🔢 Últimos números: {', '.join(map(str, results))}"
                        for chat_id in chat_ids:
                            if chat_id in ALLOWED_CHAT_IDS:
                                send_telegram_message(chat_id, message)
                except Exception as e:
                    print(f"Erro ao monitorar {id_roleta}: {e}")
            
            await asyncio.sleep(5)

async def main():
    """Executa o monitoramento das roletas."""
    roletas = [
        "evolution-auto-roulette", "immersive-roulette", "evolution-roulette", 
        "evolution-speed-auto-roulette", "evolution-auto-roulette-vip",  
        "evolution-roleta-ao-vivo", "evolution-speed-roulette", "ruleta-en-espanol", 
        "evolution-vip-roulette", "ruleta-bola-rapida-en-vivo"
    ]
    await asyncio.gather(monitorar_roletas(roletas), update_chats())

asyncio.run(main())
