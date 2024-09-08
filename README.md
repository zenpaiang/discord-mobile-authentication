# discord mobile authentication

a library to interact with discord's mobile QR login system

# library

this library works on a event basis

usage: `@client.event(<event name>)`

valid events:

1. `connect` (library connects to the discord api)
2. `pending` (qr code is created)
3. `scanned` (qr code is scanned by a user)
4. `finish` (login is approved and token is sent)
5. `cancel` (login is not approved)

# usage

follow the example in `example.py`