import FreeRooms

from dotenv import load_dotenv
from datetime import datetime, timedelta, time
from itertools import groupby
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters, ConversationHandler

from apscheduler.schedulers.background import BackgroundScheduler
import asyncio

#from .env file 
load_dotenv()
TOKEN = os.getenv("TOKEN")

#here we store the info scraped via FreeRooms
RotBuf = []

#Unicode Hex Values for icons
# chr(0x1F4CC) = 📌
# chr(0x1F3DB) = 🏛️
# chr(0x1F4CA) = 📊
# chr(0x1F622) = 😢
# chr(0x1F424) = 🐤
# chr(0x1F423) = 🐣
# chr(0x2705)  = ✅
# chr(0x274C)  = ❌

################################################################################################

async def start(update: Update, context:  ContextTypes.DEFAULT_TYPE):
    #displays welcome message and main menu (inline keyboard)

    layout = [[InlineKeyboardButton("TODAY", callback_data="today")] if datetime.now().strftime("%A") not in ["sunday", "domenica"] and datetime.now().time() < time(20,30) else None,
              [InlineKeyboardButton("TOMORROW", callback_data="tomorrow")] if (datetime.now() + timedelta(days=1)).strftime("%A") not in ["sunday", "domenica"] else None]

    keyboard = InlineKeyboardMarkup([btn for btn in layout if btn != None])

    msg_text = f"""
*Quack\!* {chr(0x1F424)}
This cute little duck is here to help you find free rooms at PoliTO and have a peaceful study session\.
_By Fra Ricca & Leo Scotti_

If you need further info try using /help command\!"""

    await update.message.reply_text(text=msg_text, reply_markup=keyboard, parse_mode="MarkdownV2")


async def quack_help(update: Update, context:  ContextTypes.DEFAULT_TYPE):
    #displays help message
    msg_text = f"""
*QUACK\!* 

To find free rooms use the commands or the inline keyboard\.

If you want info about a specific room, you can *text me directly* its name\.
_unfortunately because I'm still under development if a room is never free, neither today nor tomorrow, i'll think it doesn't exist_

*COMMANDS*
/start \- shows the main menu's inline keyboard
/help \- shows this message
/freetoday \- shows the rooms that today are free until closing time
/freetomorrow \- shows the rooms that tomorrow are free all day long

*INLINE KEYBOARD*
You can find the Inline Keyboard in the main menu using the /start command\.
You can chose between *today* and *tomorrow* context menus, 
then search *by time\-slot* or *by room type*\.

*INFO*
This bot was born to help you find a peaceful place to study\.
We scrape the official data from [swas\.polito](https://www.swas.polito.it/dotnet/orari_lezione_pub/RicercaAuleLiberePerFasceOrarie.aspx)

*OPEN SOURCE*
This project is entirely open source, chek out our [GitHub](https://github.com/QuackPolito/FreeRooms)\!\!

*CREDITS*
_Code by Fra Ricca and Leo Scotti_\.
_Hosted by TeeZee_\.
_In Love with AESA\-Torino_\.
"""
    await update.message.reply_text(text=msg_text, parse_mode="MarkdownV2")


async def all(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False):
    #returns all the info about rooms disponibility
    msg_text = ""
    queries = list(RotBuf[0].keys())

    await update.callback_query.message.reply_text(text=msg_text, parse_mode='MarkdownV2')



async def free(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False) -> int:
    #finds all free rooms today (from now till closure)

    if datetime.now().strftime("%A") in ["sunday", "domenica"]:
        msg_text = f"*PoliTO is closed on sunday\!* {chr(0x1F423)}\nTo find tomorrow's available rooms\nuse /freetomorrow command"

    elif datetime.now().time() < datetime.strptime("20:30", "%H:%M").time():
        F_rooms = FreeRooms.check_free_from_now(RotBuf[0])
        if F_rooms != []:
            txt = []
            for key, group in groupby(F_rooms, key=lambda r: ''.join(filter(str.isalpha, r.rstrip(',')))):
                txt.append(f'\n{chr(0x1F4CC)} *{key if key != "" else "MAIN"} {"ROOMS" if "LAIB" not in key else ""}*')
                txt.append("  ".join(group))
            msg_text = chr(0x1F3DB) + " *FREE ROOMS TODAY*\n" + "\n".join(txt)
        else:
            msg_text = f"*Quack {chr(0x1F622)}*\nNo rooms are fully available until closing time"

    else:
        msg_text = f"*PoliTO has closed for today\!* {chr(0x1F423)}\nTo find tomorrow's available rooms\nuse /freetomorrow command"

    if not from_callback:
        await update.message.reply_text(text=msg_text, parse_mode='MarkdownV2', reply_markup=ReplyKeyboardRemove())
    else: 
        await update.callback_query.message.reply_text(text=msg_text, parse_mode='MarkdownV2')

    return ConversationHandler.END


async def tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False) -> int:
    #finds all day long free rooms for tomorrow

    if (datetime.now() + timedelta(days=1)).strftime("%A")  not in ["sunday", "domenica"]:
        F_rooms = FreeRooms.check_free_all_day(RotBuf[1])
        if F_rooms != []:
            txt = []
            for key, group in groupby(F_rooms, key=lambda r: ''.join(filter(str.isalpha, r.rstrip(',')))):
                txt.append(f'\n{chr(0x1F4CC)} *{key if key != "" else "MAIN"} {"ROOMS" if "LAIB" not in key else ""}*')
                txt.append("  ".join(group))
            msg_text = chr(0x1F3DB) + " *FREE ROOMS TOMORROW*\n" + "\n".join(txt)
        else:
            msg_text = f"*Quack {chr(0x1F622)}*\nNo rooms are available for the entire day"

    else:
        msg_text = f"*PoliTO is closed on sunday\!* {chr(0x1F423)}"

    if not from_callback:
        await update.message.reply_text(text=msg_text, parse_mode='MarkdownV2', reply_markup=ReplyKeyboardRemove())
    else: 
        await update.callback_query.message.reply_text(text=msg_text, parse_mode='MarkdownV2')
    
    return ConversationHandler.END

################################################################################################

async def format_room_info(query:str, t="-1") -> str :
    #formats disponibility info for a given room (query) for the given day {0: today, 1: tomorrow, -1: both})

    # chr(0x2705) = ✅
    # chr(0x274C) = ❌

    text0 = []
    text1 = []

    #today
    if t in ["-1", "0"]:
        today_slots = FreeRooms.get_available_slots(0)
        try:
            d0 = RotBuf[0][query][-len(today_slots):]
        except KeyError:
            d0 = ["0"]*len(today_slots)

        for i, slot in enumerate(today_slots):
            text0.append(slot.replace("-", " \- ") + "  " + (chr(0x2705) if d0[i] == "1" else chr(0x274C)))
        
    #tomorrow
    if t in ["-1", "1"]:
        tomorrow_slots = FreeRooms.get_available_slots(1)
        try:
            d1 = RotBuf[1][query]
        except KeyError:
            d1 = ["0"]*len(tomorrow_slots)

        for i, slot in enumerate(tomorrow_slots):
            text1.append(slot.replace("-", " \- ") + "  " + (chr(0x2705) if d1[i] == "1" else chr(0x274C)))
        
    text = f"{chr(0x1F4CA)} *ROOM {query}*\n\n" + (("*TODAY*\n" + "\n".join(text0) + "\n\n") if text0 != [] else "") + ("*TOMORROW*\n" +"\n".join(text1) if text1 != [] else "")

    return text

################################################################################################

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #handles inline keyboard's buttons' callbacks, managing submenus
    query = update.callback_query
    await query.answer()

    if query.data == "main":
        #main menu
        layout = [[InlineKeyboardButton("TODAY", callback_data="today")] if datetime.now().strftime("%A") not in ["sunday", "domenica"] and datetime.now().time() < time(20,30) else None,
              [InlineKeyboardButton("TOMORROW", callback_data="tomorrow")] if (datetime.now() + timedelta(days=1)).strftime("%A") not in ["sunday", "domenica"] else None] 
        
        new_keyboard = InlineKeyboardMarkup(layout)
        
        await query.edit_message_reply_markup(new_keyboard)


    elif query.data == "today":
        #today context menu
        new_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("FREE TODAY UNTIL CLOSING TIME", callback_data="free_today")],
                [InlineKeyboardButton("By Time Slot", callback_data="by_time_slot_today"), 
                InlineKeyboardButton("By Room", callback_data="by_room_today")],
                [InlineKeyboardButton("BACK", callback_data="main")]])
        
        await query.edit_message_reply_markup(new_keyboard)

    elif query.data == "tomorrow":
        #tomorrow context menu
        new_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("FREE TOMORROW ALL DAY LONG", callback_data="free_tomorrow")],
                [InlineKeyboardButton("By Time Slot", callback_data="by_time_slot_tomorrow"), 
                InlineKeyboardButton("By Room", callback_data="by_room_tomorrow")],
                [InlineKeyboardButton("BACK", callback_data="main")]])
        
        await query.edit_message_reply_markup(new_keyboard)

    elif query.data == "free_today":
        await free(update, context, from_callback=True)

    elif query.data == "free_tomorrow":
        await tomorrow(update, context, from_callback=True)

    elif query.data.startswith("by_time_slot"):
        #time-slots submenu
        t = 0 if query.data.endswith("today") else 1 #target day (0:today, 1:tomorrow)
        layout = [
            [InlineKeyboardButton("08:30 - 10:00", callback_data=f"slot_0_{t}"), InlineKeyboardButton("10:00 - 11:30", callback_data=f"slot_1_{t}")],
            [InlineKeyboardButton("11:30 - 13:00", callback_data=f"slot_2_{t}"), InlineKeyboardButton("13:00 - 14:30", callback_data=f"slot_3_{t}")],
            [InlineKeyboardButton("14:30 - 16:00", callback_data=f"slot_4_{t}"), InlineKeyboardButton("16:00 - 17:30", callback_data=f"slot_5_{t}")],
            [InlineKeyboardButton("17:30 - 19:00", callback_data=f"slot_6_{t}"), InlineKeyboardButton("19:00 - 20:30", callback_data=f"slot_7_{t}")],
            [InlineKeyboardButton("BACK", callback_data="today" if t == 0 else "tomorrow")]]
        available_slots = FreeRooms.get_available_slots(t)
        new_keyboard = InlineKeyboardMarkup([[btn for btn in row if btn.text.replace(" - ", "-") in available_slots or btn.text == "BACK"] for row in layout]) 
        await query.edit_message_reply_markup(new_keyboard)

    elif query.data.startswith("by_room"):
        #room-type submenu
        t = 0 if query.data.endswith("today") else 1 #target day (0:today, 1:tomorrow)
        new_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Main Lecture Rooms", callback_data=f"rooms_n_{t}")],
            [InlineKeyboardButton("A Rooms", callback_data=f"rooms_A_{t}"),InlineKeyboardButton("B  Rooms", callback_data=f"rooms_B_{t}")],
            [InlineKeyboardButton("C Rooms", callback_data=f"rooms_C_{t}"),InlineKeyboardButton("D  Rooms", callback_data=f"rooms_D_{t}")],
            [InlineKeyboardButton("I Rooms", callback_data=f"rooms_I_{t}"),InlineKeyboardButton("M  Rooms", callback_data=f"rooms_M_{t}")],
            [InlineKeyboardButton("N Rooms", callback_data=f"rooms_N_{t}"),InlineKeyboardButton("P  Rooms", callback_data=f"rooms_P_{t}")],
            [InlineKeyboardButton("R Rooms", callback_data=f"rooms_R_{t}"),InlineKeyboardButton("S  Rooms", callback_data=f"rooms_S_{t}")],
            [InlineKeyboardButton("T Rooms", callback_data=f"rooms_T_{t}"),InlineKeyboardButton("LAIB", callback_data=f"rooms_LAIB_{t}")],
            [InlineKeyboardButton("BACK", callback_data="today" if t == 0 else "tomorrow")]])
        
        await query.edit_message_reply_markup(new_keyboard)

    elif query.data.startswith("slot_"):
        slot = int(query.data.split("_")[1]) #target time slot
        t = int(query.data[-1]) #target day (0:today, 1:tomorrow)
        FreeInSlot = FreeRooms.check_by_slot(slot, RotBuf[0])
        if FreeInSlot != []:
            txt = []
            for key, group in groupby(FreeInSlot, key=lambda r: ''.join(filter(str.isalpha, r.rstrip(',')))):
                txt.append(f'\n{chr(0x1F4CC)} *{key if key != "" else "MAIN"} {"ROOMS" if "LAIB" not in key else ""}*')
                txt.append(" * * ".join(group))
            msg_text = chr(0x1F3DB) + f' *FREE ROOMS {"TODAY" if t == 0 else "TOMORROW"} \({FreeRooms.slots[slot]}\)*\n'.replace("-", "\-") + "\n".join(txt)
        else:
            msg_text = f'*Quack* {chr(0x1F622)}\n{"Today" if t == 0 else "Tomorrow"} there are no free rooms in this time-slot \({FreeRooms.slots[slot]}\)'.replace("-", "\-")

        await update.callback_query.message.reply_text(text=msg_text, parse_mode='MarkdownV2')

    elif query.data.startswith("rooms_"):
        room_type = query.data.split("_")[1]
        t = int(query.data[-1]) #target day (0:today, 1:tomorrow)
        
        if room_type == "n":
            selected_rooms = list(filter(lambda room: room.isdigit(), RotBuf[t]))
        elif room_type == "LAIB":
            selected_rooms = list(filter(lambda room: "LAIB" in room, RotBuf[t]))
        else:
            control = lambda room: room_type in room and "LAIB" not in room and (list(set(RotBuf[t][room][-len(FreeRooms.get_available_slots(0)):])) != ["0"] or t == 1)
            selected_rooms = list(filter(control, RotBuf[t]))

        if len(selected_rooms) != 0:
            selected_rooms.sort(key=FreeRooms.sort_by_type)
            layout = [[InlineKeyboardButton(x, callback_data= f'room_{x}_{t}')] for x in selected_rooms]
        else:
            layout = [[InlineKeyboardButton(f'{chr(0x274C)} THERE ARE NO FREE {room_type} {"ROOMS" if room_type != "LAIB" else ""}  {chr(0x274C)}', callback_data="empty")]]
        layout.append([InlineKeyboardButton("BACK", callback_data="by_room_" + ("today" if t == 0 else "tomorrow"))])
        new_keyboard = InlineKeyboardMarkup(layout)

        await query.edit_message_reply_markup(new_keyboard)

    elif query.data.startswith("room_"):
        room = query.data.split("_")[1]
        t = query.data[-1]
        msg_text = await format_room_info(room, t=t)

        await update.callback_query.message.reply_text(text=msg_text, parse_mode='MarkdownV2')

################################################################################################

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #handles direct text msg: if it's a room name returns disponibility, else help msg
    query = update.message.text.upper().strip()

    if query in RotBuf[0].keys() or query in RotBuf[1].keys():
        text = await format_room_info(query)
            
    #QUACK! That's an easer egg
    elif "QUACK" in query:
        text = chr(0x1F423) + " *Quack\!*"

    else:
        text= f"{chr(0x274C)} *That's not a room\!*\nTry with a correct room name or use the /start command instead"

    await update.message.reply_text(text=text, parse_mode='MarkdownV2')
     
################################################################################################

def schedule_daily_task(): 
    #schedules daily refresh of the Rotary Buffer
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: asyncio.run(Rotate()),"cron",hour=0, minute=1)
    scheduler.start()

async def Rotate():
    #refreshes Rotary Buffer
    RotBuf[0] = RotBuf[1]
    try:
        RotBuf[1] = FreeRooms.scrape_data(1)[0]
    except:
        RotBuf[1] = []

################################################################################################

def main() -> None:
    bot = ApplicationBuilder().token(TOKEN).build()

    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("help", quack_help))
    bot.add_handler(CommandHandler("freetoday", free))
    bot.add_handler(CommandHandler("freetomorrow", tomorrow))
    bot.add_handler(CallbackQueryHandler(button_callback))
    bot.add_handler(MessageHandler(filters.TEXT, text_message_handler))

    schedule_daily_task()

    try:
        RotBuf.append(FreeRooms.scrape_data(0)[0])
    except:
        RotBuf.append([])
    try:
        RotBuf.append(FreeRooms.scrape_data(1)[0])
    except:
        RotBuf.append([])

    print("bot running!!")
    bot.run_polling(allowed_updates=Update.ALL_TYPES)



if __name__ == "__main__":
    main()
