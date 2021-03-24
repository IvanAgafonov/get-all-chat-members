# importing all required libraries
from boto.s3.connection import S3Connection
import os
s3 = S3Connection(os.environ['S3_KEY'], os.environ['S3_SECRET'])
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import InputPeerUser, InputPeerChannel, ChannelParticipantsSearch
from telethon import TelegramClient, sync, events
from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
import asyncio
from telethon import functions, types
import time

# get your api_id, api_hash, token
# from telegram as described above
api_id = os.environ['api_id']
api_hash = os.environ['api_hash']

# your phone number
phone = os.environ['phone']

# creating a telegram session and assigning
# it to a variable client
client = TelegramClient('session', api_id, api_hash)

# connecting and building the session
client.connect()

# in case of script ran first time it will
# ask either to input token or otp sent to
# number or sent or your telegram id 
if not client.is_user_authorized():
    client.send_code_request(phone)

    # signing in the client
    client.sign_in(phone, input('Enter the code: '))


async def get_members(dialog):
    offset = 0
    limit = 100
    all_participants = []

    if not dialog.is_channel:
        participants = await client.get_participants(dialog, aggressive=True)
        all_participants = participants
    else:
        while True:
            participants = await client(GetParticipantsRequest(
                dialog, ChannelParticipantsSearch(''), offset, limit, hash=0
            ))
            if not participants.users:
                break
            all_participants.extend(participants.users)
            offset += len(participants.users)
    user_names = []
    for participant in all_participants:
        if participant.username is not None:
            user_names.append(participant.username)
    message = ""
    messages = []
    cur_len = 0
    for username in user_names:
        if username != "GetAllChatMembers":
            message += "@" + username + " "
            cur_len += len("@" + username + " ")
        if cur_len > 4000:
            messages.append(message)
            message = ""
            cur_len = 0
    if message != "":
        messages.append(message)
    return messages


async def get_dialog_by_name(name):
    dialogs = await client.get_dialogs()
    for dialog in dialogs:
        if hasattr(dialog, "entity"):
            if hasattr(dialog.entity, "username"):
                if dialog.entity.username == name:
                    return dialog
    return None


async def get_dialog_by_id(id):
    dialogs = await client.get_dialogs()
    for dialog in dialogs:
        if hasattr(dialog, "entity"):
            if hasattr(dialog.entity, "id"):
                if dialog.entity.id == id:
                    return dialog
    return None


@client.on(events.NewMessage)
async def handler(event):
    if event.is_private:
        message = event.message.message
        argv = message.split(" ")
        if len(argv) != 1:
            return
        chat = None
        hash = None
        if "/joinchat/" in argv[0]:
            hash = argv[0].split("/")[-1]
            try:
                updates = await client(ImportChatInviteRequest(hash))
                chat = updates.chats[0]
                chat_id = chat.id
            except Exception as e:
                updates = await client(CheckChatInviteRequest(hash))
                chat_id = updates.chat.id
            chat = await get_dialog_by_id(chat_id)
        if "@" in argv[0]:
            chat_name = argv[0][1:]
            try:
                await client(functions.channels.JoinChannelRequest(
                    channel=chat_name
                ))
            except Exception as e:
                pass
            chat = await get_dialog_by_name(chat_name)
        res = await get_members(chat)
        for mes in res:
            await event.reply(mes)
            time.sleep(1)
        if hash is not None:
            await client(functions.channels.LeaveChannelRequest(
                chat
            ))
        else:
            await client(functions.channels.LeaveChannelRequest(
                chat
            ))


client.loop.run_forever()
