import discord_ma
import requests
import asyncio
import qrcode

client = discord_ma.MobileAuth()

@client.event("connect")
def connect():
    print("connected to websocket")

@client.event("pending")
def pending(url):
    img = qrcode.make(url)
    img.show()
    
@client.event("scanned")
def scanned(user):
    print("code scanned")
    
@client.event("finish")
def finished(token):
    print(f"token: {token}")
    
    headers = {
        "Authorization": token
    }
    
    resp = requests.get("https://discord.com/api/users/@me", headers=headers)
    
    print(resp.text)
    
@client.event("cancel")
def cancel():
    print("cancelled")
    
asyncio.run(client.connect())