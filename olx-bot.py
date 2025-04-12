import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import logging
import random

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- KONFIGURACJA TELEGRAM ---
TELEGRAM_TOKEN = "7598539276:AAEMIbDymj0mZLq_dz8ozpHhmn89eJTIy9U"
TELEGRAM_CHAT_ID = "7495057991"

# Globalna lista do śledzenia wysłanych wiadomości
sent_messages = []

def send_telegram_message(message: str):
    """Wysyła wiadomość na Telegrama i zapisuje informacje o niej"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        
        # Store message info for future deletion
        message_data = {
            'message_id': response.json()['result']['message_id'],
            'timestamp': datetime.now(),
            'chat_id': TELEGRAM_CHAT_ID
        }
        sent_messages.append(message_data)
        return message_data
    except Exception as e:
        logging.error(f"Błąd wysyłania wiadomości na Telegram: {e}")
        return None

def cleanup_old_messages():
    """Usuwa wiadomości starsze niż 30 minut"""
    global sent_messages
    now = datetime.now()
    cutoff = now - timedelta(minutes=30)
    
    messages_to_keep = []
    
    for msg in sent_messages:
        if msg['timestamp'] < cutoff:
            try:
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteMessage"
                payload = {
                    'chat_id': msg['chat_id'],
                    'message_id': msg['message_id']
                }
                requests.post(url, data=payload)
            except Exception as e:
                logging.error(f"Błąd usuwania wiadomości {msg['message_id']}: {e}")
        else:
            messages_to_keep.append(msg)
    
    sent_messages = messages_to_keep

def format_offer_message(offer: dict) -> str:
    """Formatuje ofertę do wiadomości Telegram"""
    return (
        f"<b>🎮 Nowa oferta Nintendo Switch 🎮</b>\n\n"
        f"<b>📌 Tytuł:</b> {offer['tytul']}\n"
        f"<b>💰 Cena:</b> {offer['cena']}\n"
        f"<b>📅 Data dodania:</b> {offer['czas']}\n\n"
        f"<a href='{offer['link']}'>🔗 Zobacz ofertę</a>"
    )

def pobierz_ogloszenia(z_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(z_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    ogloszenia = []
    for offer in soup.select("div[data-cy='l-card']"):
        try:
            if offer.select_one("span[data-testid='adCard-featured']"):
                continue

            czas_tag = offer.select_one("p[data-testid='location-date']")
            czas_txt = czas_tag.get_text(strip=True) if czas_tag else ""

            if "Odświeżono" in czas_txt or "Dzisiaj" not in czas_txt:
                continue

            # Parsowanie i korekta czasu (+2 godziny)
            if "Dzisiaj o " in czas_txt:
                godzina_str = czas_txt.split("Dzisiaj o ")[1]
                try:
                    stara_godzina = datetime.strptime(godzina_str, "%H:%M")
                    nowa_godzina = (stara_godzina.hour + 2) % 24
                    nowa_minuta = stara_godzina.minute
                    czas_txt = f"Dzisiaj o {nowa_godzina:02d}:{nowa_minuta:02d}"
                except ValueError:
                    pass  # Zostawiamy oryginalny czas jeśli parsowanie się nie uda

            cena_tag = offer.select_one("p[data-testid='ad-price']")
            cena = cena_tag.get_text(strip=True) if cena_tag else "Brak"

            link_tag = offer.select_one("a")
            link = "https://www.olx.pl" + link_tag["href"].split('#')[0] if link_tag else "Brak"

            tytul_tag = offer.select_one("a h6") or offer.select_one("a h4")
            tytul = tytul_tag.get_text(strip=True) if tytul_tag else "Brak"

            ogloszenie = {
                "tytul": tytul,
                "cena": cena,
                "czas": czas_txt,
                "link": link
            }

            ogloszenia.append(ogloszenie)
        except Exception as e:
            logging.error(f"Błąd przy przetwarzaniu ogłoszenia: {e}")
            continue

    return ogloszenia[:5]

def wyswietl_ogloszenia(ogloszenia):
    print(f"\n🕒 Odświeżono: {datetime.now().strftime('%H:%M:%S')}")
    print("=====================================")
    if not ogloszenia:
        print("Brak nowych ogłoszeń.")
    for i, ogloszenie in enumerate(ogloszenia, 1):
        print(f"   Tytuł: {ogloszenie['tytul']}")
        print(f"   Cena: {ogloszenie['cena']}")
        print(f"   Dodano: {ogloszenie['czas']}")
        print(f"   Link: {ogloszenie['link']}\n")

# 🔗 Link do OLX (np. szukanie Nintendo)
URL_OLX = "https://www.olx.pl/elektronika/gry-konsole/konsole/q-nintendo-switch/?search[order]=created_at:desc"
widziane_linki = set()

print("🔍 Bot OLX uruchomiony. Czekam na nowe ogłoszenia...")
send_telegram_message(f"🤖 <b>Bot OLX uruchomiony</b>. Czekam na nowe oferty...")

while True:
    try:
        wszystkie = pobierz_ogloszenia(URL_OLX)
        nowe = []

        for ogloszenie in wszystkie:
            if ogloszenie["link"] not in widziane_linki:
                nowe.append(ogloszenie)
                widziane_linki.add(ogloszenie["link"])
                send_telegram_message(format_offer_message(ogloszenie))

        wyswietl_ogloszenia(nowe[:5])
        
        # Czyszczenie starych wiadomości
        cleanup_old_messages()
        
        time.sleep(random.randint(50, 75))

    except KeyboardInterrupt:
        print("\n🛑 Zatrzymano bota.")
        send_telegram_message(f"🛑 <b>Bot OLX zatrzymany</b>")
        break
    except Exception as e:
        logging.error(f"Błąd główny: {e}")
        time.sleep(random.randint(50, 75))