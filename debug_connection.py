"""Hızlı bağlantı testi — filtresiz, ilk 5 mesajı göster."""
import asyncio, json, os
from dotenv import load_dotenv
import websockets

load_dotenv()
API_KEY = os.getenv("AISSTREAM_API_KEY")
print(f"API Key: '{API_KEY}'")  # boşluk var mı görelim
print(f"Uzunluk: {len(API_KEY) if API_KEY else 0}")

async def test():
    url = "wss://stream.aisstream.io/v0/stream"
    sub = {
        "APIKey": API_KEY,
        "BoundingBoxes": [[[-90.0, -180.0], [90.0, 180.0]]],  # Tüm dünya [lat,lon]
    }
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps(sub))
        print("Bağlandı, bekleniyor...\n")
        count = 0
        async for msg in ws:
            data = json.loads(msg)
            print(json.dumps(data, indent=2)[:400])
            print("---")
            count += 1
            if count >= 3:
                break
    print("Test tamamlandı.")

asyncio.run(test())
