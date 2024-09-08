from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from . import exc
import websockets
import requests
import hashlib
import asyncio
import base64
import random
import time
import json
import re

class MobileAuth:
    def __init__(self):
        self._ws = None
        self._events = {}
        self._valid_events = [
            "connect",
            "pending",
            "scanned",
            "finish",
            "cancel"
        ]
        
    def _add_event(self, name, func):
        self._events[name] = func
        
    def _run_event(self, name, *args):
        if name in self._events:
            self._events[name](*args)       
        
    def event(self, event: str):
        def decorator(f, *args):            
            if event in self._valid_events:
                self._add_event(event, f)
            else:
                raise exc.InvalidEventError
                
            return f

        return decorator
    
    async def connect(self):
        self._ws = await websockets.connect("wss://remote-auth-gateway.discord.gg/?v=2", origin="https://discord.com")
        
        _heartbeat_interval = 0
        _next_heartbeat = 0
        _jitter = random.random()
        
        while True:
            if _heartbeat_interval != 0:
                if time.time() >= _next_heartbeat:
                    await self._ws.send(json.dumps({"op": "heartbeat"}))
                    
                    await self._ws.recv()
                    
                    _next_heartbeat = time.time() + ((_heartbeat_interval * _jitter) / 1000)
            
            try:
                rec = await asyncio.wait_for(self._ws.recv(), timeout=0.2)
                data = json.loads(rec)
            except Exception as _:
                data = None
                
            if data:
                match data["op"]:
                    case "hello":   
                        keypair = RSA.generate(bits=2048, e=0x01001)
                        public_key = "".join(keypair.public_key().export_key().decode().strip().split("\n")[1:-1])
                    
                        await self._ws.send(json.dumps({"op": "init", "encoded_public_key": public_key}))
                        
                        _heartbeat_interval = data["heartbeat_interval"]
                        _next_heartbeat = time.time() + ((_heartbeat_interval * _jitter) / 1000)
                        
                        self._run_event("connect")
                    case "nonce_proof":
                        cipher = PKCS1_OAEP.new(keypair, hashAlgo=SHA256)
                        decryptedNonce = cipher.decrypt(base64.b64decode(data["encrypted_nonce"]))
                        
                        nonceHash = hashlib.sha256()
                        
                        nonceHash.update(decryptedNonce)
                        
                        nonceHash1 = re.sub("=+$", "", base64.b64encode(nonceHash.digest(), b"-_").decode())
                        
                        await self._ws.send(json.dumps({"op": "nonce_proof", "proof": nonceHash1}))
                    case "pending_remote_init":
                        fingerprint = data["fingerprint"]
                        
                        url = f"https://discord.com/ra/{fingerprint}"
                        
                        self._run_event("pending", url)
                        
                    case "pending_ticket":                
                        cipher = PKCS1_OAEP.new(keypair, hashAlgo=SHA256)
                        decryptedUser = cipher.decrypt(base64.b64decode(data["encrypted_user_payload"])).decode()
                        userData = decryptedUser.split(":")
                        
                        self._run_event("scanned", userData)
                    case "pending_login":
                        cipher = PKCS1_OAEP.new(keypair, hashAlgo=SHA256)
                        
                        payload = {
                            "ticket": data["ticket"]
                        }
                        
                        headers = {
                            "Origin": "https://discord.com",
                            "Content-Type": "application/json"
                        }
                        
                        resp = requests.post("https://discord.com/api/v9/users/@me/remote-auth/login", headers=headers, data=json.dumps(payload))
                                        
                        decryptedToken = cipher.decrypt(base64.b64decode(resp.json()["encrypted_token"])).decode()
                        
                        self._run_event("finish", decryptedToken)
                    case "cancel":
                        self._run_event("cancel")