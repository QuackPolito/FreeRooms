from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

from datetime import datetime, timedelta
import locale
import time

#swas.polito url
URL = "https://www.swas.polito.it/dotnet/orari_lezione_pub/RicercaAuleLiberePerFasceOrarie.aspx"

#time slots table
slots = ['08:30-10:00', '10:00-11:30', '11:30-13:00', '13:00-14:30', '14:30-16:00', '16:00-17:30', '17:30-19:00', '19:00-20:30']


def start():
    #starting selenium driver with custom options

    global driver
    options = Options()
    options.add_argument("--headless=new") #to hide chrome 
    options.add_argument("--log-level=3") #to block info and waring outputs
    options.add_experimental_option('excludeSwitches', ['enable-logging']) #to block info and waring outputs
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(15) 

    print(f'[i] Selenium Driver online and running!')


def scrape_data(delta_time):
    #scraping data from swas.polito

    start() #starting selenium driver

    #defining local variables
    #will be returned and used as arguments for further data elab.
    Disponibiliti = dict()
    RoomsPerSlot = dict()
    Rooms = []

    #picking the target date
    locale.setlocale(locale.LC_TIME, "it_IT.UTF-8")  
    day = (datetime.now() + timedelta(days=delta_time)).strftime("%A %d %B %Y")
    day = day.replace(" 0", " ").encode("latin1").decode("utf-8")
    print(f'[i] target date set at: {day}')

    #opening swas.polito
    driver.get(URL)
    print('[i] Successfully conncted to swas.polito')

    if delta_time:
        #opening calendar dial
        print('    clicking calendar...')
        time.sleep(.5)
        Calendario = driver.find_element(by=By.ID, value="Pagina_img_DataRif")
        Calendario.click()

        #clicking date btn inside the calendar
        print('    clicking date...')
        time.sleep(.5)
        daytoclick = driver.find_elements(by=By.CLASS_NAME, value="ajax__calendar_day")
        for element in daytoclick:
            if day in element.get_attribute("title"):
                quack = element
                break

        quack.click()

    #accepting boring cookies :(
    print('    accepting cookies...')
    time.sleep(.5)
    Cookies = driver.find_element(by=By.CLASS_NAME, value="cb-enable")
    Cookies.click()

    print('    looking into slots...')
    
    #looking for available slots (expired ones won't show up in swas)
    if delta_time == 0:
        now = datetime.now().time()
        available_slots = list(filter(lambda slot: datetime.strptime(slot.split("-")[1], "%H:%M").time() > now , slots))
        n = len(available_slots)
    else:
        n = 8 #if target is tomorrow  

    for slot_n in range(0,n):
        try:
            #expanding time slot
            slot_id = "Pagina_gv_AuleLibere_img_ShowHideAule_" + str(slot_n)
            Button = driver.find_element(by=By.ID, value=slot_id)
            driver.execute_script("arguments[0].scrollIntoView(true);", Button)
            time.sleep(.5)
            Button.click()
            time.sleep(.5)

            #getting actual room data
            RoomsBox_id = "Pagina_gv_AuleLibere_lbl_AuleLibere_" + str(slot_n)
            RoomsList = driver.find_element(by=By.ID, value=RoomsBox_id)

            RoomsPerSlot[slots[slot_n]] = RoomsList.text.strip().split(", ")
            for room in RoomsPerSlot[slots[slot_n]]:
                if room not in Rooms:
                    Rooms.append(room)

        except Exception as ex:
            print(f'[!] Exception Occurred at ({datetime.now().strftime("%H:%M")}) while scraping data: {type(ex).__name__}')
            pass

    driver.quit()
    print(f'[i] Selenium Driver shutdown completed.')

    for room in set(Rooms):
        Disponibiliti[room] = ["1" if room in RoomsPerSlot[slot] else "0" for slot in slots[:n]]
        print(f'[+] {room+":":<7} {Disponibiliti[room]}')
    print(f'[i] Scraping successfully completed.')

    return Disponibiliti, Rooms, RoomsPerSlot

##################################################################################################################

def check_by_slot(slot_n:int, data:dict) -> list:
    """returns free rooms for a given time slot"""
    n = slot_n-(8-len(list(data.values())[0])) #if swas gave less than 8 slots
    free = list(filter(lambda room: data[room][n] == "1", data)) 
    free.sort(key=sort_by_type)
    return free

def check_by_room(room:int, data:dict) -> list:
    """returns availability data for a given room"""
    schedule = data[room]
    for i, status in enumerate(schedule):
        print(f'Slot {i+1} (slots[i]): {"Free" if status == "1" else "Occupied"}')
    return schedule

def check_free_all_day(data:dict) -> list:
    """returns all rooms free all day long"""
    AllDayFreeRooms = list(filter(lambda room: set(data[room]) ==  {"1"}, data))
    AllDayFreeRooms.sort(key=sort_by_type)
    return AllDayFreeRooms

def check_free_from(start:int, data:dict) -> list:
    """returns all rooms free from the given time slot till closure"""
    start = start-(8-len(list(data.values())[0])) #if swas gave less than 8 slots
    if start > 0: 
        FreeRoomsFrom = list(filter(lambda room: set(data[room][start-(8-len(data[room])):]) == {"1"}, data)) #start must be an integer in range(0,6)
    else:  #if selected starting slot is already expired
        FreeRoomsFrom = list(filter(lambda room: set(data[room]) ==  {"1"}, data))
    FreeRoomsFrom.sort(key=sort_by_type)
    return FreeRoomsFrom

def check_free_from_now(data:dict) -> list:
    """returns all rooms free from current time slot till closure"""
    now = datetime.now().time()
    current_slot = list(filter(lambda slot: datetime.strptime(slot.split("-")[1], "%H:%M").time() > now , slots))[0]
    start = slots.index(current_slot)
    FreeRoomsFromNow = check_free_from(start, data)
    return FreeRoomsFromNow

def sort_by_type(room):
    """custom sorting function: by room type and by room number"""
    is_laib = room.startswith("LAIB")
    number_part = ''.join(filter(str.isdigit, room))
    letter_part = ''.join(filter(str.isalpha, room))
    number = int(number_part) if number_part else 0
    return (is_laib, letter_part, number)

def get_available_slots(delta:int) -> list:
    """returns non expired time-slots"""
    if delta == 0: #today
        now = datetime.now().time()
        target = datetime.now().weekday()
        if target == 6: #saturday
            available_slots = list(filter(lambda slot: datetime.strptime(slot.split("-")[1], "%H:%M").time() > now , slots[:-3]))
        elif target == 7: #sunday
            available_slots = []
        else:
            available_slots = list(filter(lambda slot: datetime.strptime(slot.split("-")[1], "%H:%M").time() > now , slots))

    elif delta >= 1: #tomorrow or later
        target = (datetime.now() + timedelta(days=delta)).weekday()
        if target == 6: #saturday
            available_slots = slots[:-3]
        elif target == 7: #sunday
            available_slots = []
        else:
            available_slots = slots
    return available_slots


##################################################################################################################

if __name__ == "__main__":
    Disponibiliti, Rooms, RoomsPerSlot = scrape_data(0)
    print(check_free_from_now(Disponibiliti))

