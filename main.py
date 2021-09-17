#Gamemaster's Bot BETA

#library imports
import os
import gc
import subprocess
import re
import math
import importlib
import threading
import shutil
import potions

from datetime import *
from random import *
from javax.swing import JFrame, JButton, JLabel, JScrollPane, JTextArea, JPanel, JButton
from java.awt import BorderLayout,GridLayout,GridBagConstraints,GridBagLayout,FlowLayout,Dimension,Robot, Color
from sikuli import *

#basic settings
Settings.ObserveScanRate = 2
Settings.MoveMouseDelay = 0
Settings.ActionLogs = 0
Settings.InfoLogs = 0
Settings.DebugLogs = 0

#CONFIGS

#set the size of bot's debugger (complex or simple)
console_type = "complex" 

#seconds before moving to next waypoint
walk_interval = 2

#check if there is no way to the mob
check_no_way = 1

#tools
rope   = "o"  
shovel = "p"
ring   = "l"
amulet = "k"
food   = "u"
dust   = "="

#spells
cure_poison = "i"
haste       = "b"

#defines game region
game_region = Region(222,122,481,350)

#image references
#icons
in_combat_icon = "battleon.png"
paralyse_icon = "paralysed.png"
food_icon = "food.png"
poison_icon = "poison.png"
ping_icon = Pattern("ping.png").similar(0.50)

battle_target_icon = "bl_target.png"
#texts
local_chat_text = "local_chat.png"
there_is_no_way_text = Pattern("thereisnoway.png").exact()
battle_list_text = Pattern("battlelist.png").similar(0.75)
valuable_loot_text = Pattern("valuable_loot.png").similar(0.90)
no_mana_text = Pattern("noenoughmana.png").similar(0.90)
#images
life_mana_img = Pattern("life_mana_bars.png").exact()
add_zoom_img = Pattern("add_zoom.png").exact()
sub_zoom_img = Pattern("sub_zoom.png").exact()
minimap_ref_img = "minimap_aux.png"
store_purse_img = "store_inbox.png"
no_ring_img = "ring.png"
no_amulet_img = "amulet.png"

#PIXEL ANALYZER

def getPixelColorForAll(posX,posY):   
    pixel = Robot().getPixelColor(posX,posY)
    r = pixel.getRed()
    g = pixel.getGreen() 
    b = pixel.getBlue() 
    color = '{:02x}{:02x}{:02x}'.format(r,g,b)
    return color

def getPixelColorForHealer(posX,posY,id):

    pixel = Robot().getPixelColor(posX,posY)
    if   id == "life": return pixel.getRed()
    elif id == "mana": return pixel.getBlue() 
    else: return 0

#LOG OFF FUNCTION

def logoffFunction():
    
    if equip_region.exists(in_combat_icon):
        log("Could not logoff, waiting 10 seconds...")
        checkBattleList()
        wait(10)
        log("Trying to logoff again")
        logoffFunction()
        
    else:
        myOS = Settings.getOS()
        if myOS == OS.MAC:        
            type("3", KeyModifier.CMD + KeyModifier.SHIFT)
            type("l", KeyModifier.CMD)
        else:
           type("l", KeyModifier.CTRL) 
        log("[END OF EXECUTION]")
        #pauseExecution(0)
        global running
        running = 0

#WAYPOINT

#this method controls the entire waypoint system
def waypointManager():

    global wp
    global label
    
    if label == "go_hunt":  wpList = imported_script.label_go_hunt[wp-1]
    if label == "hunt":     wpList = imported_script.label_hunt[wp-1]
    if label == "leave":    wpList = imported_script.label_leave[wp-1]
    if label == "go_refil": wpList = imported_script.label_go_refil[wp-1]
    
    #list of possible inputs for the waypoint
    if   wpList[0] == "walk" and running == 1: walkToNextWaypoint(wpList)
    elif wpList[0] in ("rope","ladder","shovel"): waypointSpecialAction(wpList[0])
    elif wpList[0] == "drop": dropItem(wpList)
    elif wpList[0] == "talk": talkToNPC(wpList)
    elif wpList[0] == "attack": checkBattleList()
    elif wpList[0] == "deposit": depositItem(wpList[1],wpList[2])
    elif wpList[0] == "go_refil": 
        label = "go_refil"
        wp = 0
    elif wpList[0] == "refil": 
        try: buyItem(wpList[1],wpList[2])
        except: raise Exception("Could not find trade window")
    elif wpList[0] == "reset": resetRun()
    elif wpList[0] == "use_item": 
        try: click(wpList[1])
        except: log("Item not found")
    elif wpList[0] == "use_at": useAt(wpList[1],0)
    elif wpList[0] == "use_item_at": useAt(wpList[1],wpList[2])
    else: log("WARNING: error on waypoint"+str(wp)+":"+wpList[0])
       
    #Arrived at waypoint
    if label == "go_hunt" and wp >= last_go_hunt_wp:
        log("Setting label to hunt")
        label = "hunt"
        wp = 1
        
    elif label == "hunt" and wp >= last_hunt_wp:
        if drop_vials > 0 and running == 1: 
            checkBattleList()
            dropVials()
        
        log("Checking conditions to leave hunt...")
        for condition in leave_conditions:
            index = (leave_conditions.index(condition)) + 1
            log("Condition "+str(index)+": "+condition[0])
            label = checkLeaveConditions(condition[0],condition[1])
            if label == "leave": break #if a leave condition is found, shoul not check for another

        #set next wp back to 1         
        wp = 1
        
    elif label == "leave" and wp >= last_leave_wp:
        logoffFunction()
    
    else: wp+=1


def checkLeaveConditions(name,param):
    
    #check if potion
    if "potion" in name:
        
        try:
            while param >= 0:
                if name == "small health potion":    img_ref = potions.small_health_potion_dict[param]
                if name == "mana potion":            img_ref = potions.mana_potion_dict[param]
                if name == "strong mana potion":     img_ref = potions.strong_mana_potion_dict[param]
                if name == "ultimate health potion": img_ref = potions.ultimate_health_potion_dict[param]  
                #log("Checking if "+name+" <= "+str(param))
                if exists(img_ref,0): return "leave"
                else: 
                    if param == 0: param = -1
                    else: param -= param
            else: return "hunt" 
            
        except: 
            log("WARNING: ",name," not implemented!")
            return "leave"

    #if its a time-based condition (like server save)
    elif name == "time":
        return checkMachineTime(param[0],param[1])
        
    #if not a potion, use variable param as pattern
    else:
        try:
            if exists(param,0): return "leave"
            else: return "hunt"
        except:
            log("Error: Could not use parameter as pattern")
            return "leave"

#check current machine time
def checkMachineTime(interval_1,interval_2):

    current_time = datetime.now().strftime("%H:%M") 
    #print "Current time:",current_time
    if current_time >= interval_1 and current_time <= interval_2:
        return "leave"
    else:
        return "hunt"        

def useAt(param1,param2):
    #use_item: click on a position on screen. Best used with doors
    #use_item_at: uses an item on a position on screen.
    try:
        #if parameter 2 is zero, translate param1 to screen coordinates    
        if param2 == 0: click(pos_dict[param1.upper()])  
        
        #use param1 as item that will be used on param2 as coordinates
        else:
            click(param1)
            click(pos_dict[param2.upper()])
    except: log("Invalid position. See documentation for examples.")


current_zoom = -1
        
def walkToNextWaypoint(wpList):

    #wpList = [action,(img,zoom),atk]

    #The structure consists of 'walk' as action, 
    #followed by a tuple (minimap pattern and number of zoom), 
    #and lastly if it should keep an eye out for monsters, represented 
    #by 0 (in this case the bot will just walk/not attack), or 1+ (in this case
    #the bot will engange combat only if the number of monsters on battle list
    #is equal or higher than the especified)
    
    global current_zoom

    #returns the second value of the tuple (zoom)
    if wpList[1][1] != current_zoom: 

        for i in range(0,3):
            click(Location(sub_zoom.getX(),sub_zoom.getY()))
    
        for i in range(0,wpList[1][1]):
            click(Location(add_zoom.getX(),add_zoom.getY()))
    
        #update current_zoom to new value
        current_zoom = wpList[1][1]
        
    else: pass

    try:
        log("Walking to "+label+" waypoint "+str(wp))
        #return the first value of the tuple (pattern)
        click(wpList[1][0])
        hover(Location(x2,y2))

        #if there is no way to the destination, 
        #its possible that the character is trapped 
        #in this case, force an attack
        if check_no_way == 1:
            if game_region.exists(there_is_no_way_text,0.5) and running == 1:
                log("unreachable destination, possibly trapped")
                type(Key.SPACE)
                wait(0.3)
                battlelist_region.waitVanish(battle_target_icon,5)
                walkToNextWaypoint(wpList)
            else: pass

        #check if should cast haste spell
        if not use_haste: pass
        elif label in use_haste: type(haste)
        else: pass

        #check if the character is moving or not
        checkIsWalking(wpList)
        
    except: log("Could not find waypoint "+label+" "+str(wp))
    return
    
def checkIsWalking(wpList):

    global encounter
    time_stopped = 0
    
    while time_stopped != walk_interval:

        if encounter == 0: return
        
        minimap_region = Region(minimap_area_x,minimap_area_y,110,115)
        minimap_region.onChange(1,miniMapChangeHandler)
        minimap_region.somethingChanged = False
        minimap_region.observe(1)
        
        #if enters here, means char is still walking
        if minimap_region.somethingChanged:
            
            time_stopped = 0
            
            #while is walking and paralysed, use haste
            #if equip_region.exists(paralyse_icon,0): type(haste)
                     
            if wpList[2] > 0: 
                if (not game_region.exists(there_is_no_way_text,0)) and (countTargets(wpList[2]) >= wpList[2]): 
                    type(Key.ESC)
                    wait(0.3)
                    checkBattleList()
                    if running == 1: walkToNextWaypoint(wpList)
                else: wait(1)
            
        #if nothing changes on the screen for X seconds, add 1 to timer
        if not minimap_region.somethingChanged:
            time_stopped+=1
            log("Walking "+str(time_stopped)+"/"+str(walk_interval))

    else: 
        log("Arrived at waypoint")
        encounter = 0
        return


#function to verify if something is changing on screen
def miniMapChangeHandler(event):
    event.region.somethingChanged = True
    event.region.stopObserver()

def waypointSpecialAction(action): 
    if action == "rope":
        type(rope)
        click(Location(gr_center_x,gr_center_y))
        log("Using rope")
        
    if action == "ladder":
        click(Location(gr_center_x,gr_center_y))
        log("Using ladder")
        
    if action == "shovel":
        type(shovel)
        click(Location(gr_center_x,gr_center_y))
        log("Using shovel")    

    wait(1)
    return

def resetRun():
    global wp
    global label

    for condition in leave_conditions:
        index = (leave_conditions.index(condition)) + 1
        next_label = checkLeaveConditions(condition[0],condition[1])
        if next_label == "leave": break #if a condition is found, it must not check for another

    if next_label == "hunt":
        log("Restarting hunt from the beginning")
        label = "go_hunt"
        wp = 0
    else:
        label = "leave"
        
#BATTLE
in_battle = 0

def checkBattleList():

    global encounter
    global in_battle
    in_battle = 0

    if running == 1 and getPixelColorForAll(bl_slot1_x,bl_slot1_y) == "000000": 
   
        log("Attacking mob...")
        type(Key.SPACE)
        wait(0.3)
        encounter = 1

        #in case there is no way to the mob
        if check_no_way == 1: 
            if game_region.exists(there_is_no_way_text,0):
                log("Unreachable creature")
                type(Key.ESC)
                if loot_type == 3: lootAround(1)
                return

        #flag in_battle is used to start/end casting spells
        in_battle = 1
        battlelist_region.waitVanish(battle_target_icon,30)
        in_battle = 0
        #loot system
        if loot_type == 1 and label == "hunt": lootAround(1)
        if loot_type == 2 and game_region.exists(valuable_loot_text,0): lootAround(2)
        checkBattleList()

    elif running == 0: return    
    else: 
        log("Battle list is clear")
        if drop_vials == 2: dropVials()
        if encounter == 1 and loot_type == 3: lootAround(1)
        if dust_skin == 1 and label == "hunt":
            try: skinCreatureCorpse(imported_script.corpses) #list of corpse images
            except: pass
        return

def countTargets(slots):

    slot = bl_slot1_y
    num_targets = 0
     
    #log("Checking "+str(slots)+" slot(s)")
    #cycle trought battle list slots
    for i in range(slots):
        #log("\t"+"slot "+str((i+1))+"/"+str(slots))
        if getPixelColorForAll(bl_slot1_x,slot) == "000000": num_targets+=1
        slot += 22

    return num_targets
    
#LOOT

#loot_type = 0 -> ignore loot
#loot_type = 1 -> loot everything
#loot_type = 2 -> loot only valuable
#loot_type = 3 -> loot only after clearing the battle list

def lootAround(times):
    log("Looting around ("+str(times)+"x)")
    for i in range(times):
        #parameter '8' equals to 'alt + left click'
        click(pos_dict["NW"],8)
        click(pos_dict["N"],8)
        click(pos_dict["NE"],8)
        click(pos_dict["W"],8)
        click(pos_dict["C"],8)
        click(pos_dict["E"],8)
        click(pos_dict["SW"],8)
        click(pos_dict["S"],8)
        click(pos_dict["SE"],8)

#USE/CAST/SEND HOTKEYS

LTU_obj  = datetime.now()
LTU_heal_spell = datetime.now()  

#function to prevent being exhausted
def validate_hotkey(group,LTU,cd):

    global LTU_obj
    global LTU_heal_spell

    if group == "obj": diff_group = (datetime.now()- LTU_obj).total_seconds
    elif group == "heal_spell": diff_group = (datetime.now()- LTU_heal_spell).total_seconds
    else: diff_group = 99

    if diff_group < 1: return 0
    else:

        diff = (datetime.now() - LTU).total_seconds()
        if diff >= cd: return 1
        else: return 0

function_keys = ["F1","F2","F3","F4","F5","F6","F7","F8","F9","F10","F11","F12"]

function_keys_dict = {

        "F1": Key.F1,
        "F2": Key.F2,
        "F3": Key.F3,
        "F4": Key.F4,
        "F5": Key.F5,
        "F6": Key.F6,
        "F7": Key.F7,
        "F8": Key.F8,
        "F9": Key.F9,
        "F10": Key.F10,
        "F11": Key.F11,
        "F12": Key.F12
}

#HEALING AND CASTING SPELLS THREADS

#Healing thread
def healingThread(arg):

    while running == 1:
                       
        for heal in healing:

            if heal[0] == "hp": shouldHeal = lifeTest(heal[2])
            else: shouldHeal = manaTest(heal[2])
                
            if shouldHeal == 1: 
                valid = validate_hotkey(heal[4],heal[6],heal[5])
                if valid == 1:  
                    log(heal[0]+" < " +str(heal[2])+"%: Using "+str(heal[1]))
                    #
                    if heal[3] in function_keys: 
                        type(function_keys_dict[heal[3]])
                    else:
                        type(heal[3])
                    heal[6] = datetime.now()
                    
    else: print "Ending healing thread" 
                
def lifeTest(percent):

    start_life_x = life_mana_bars.getCenter().getX()+9
    end_life_x = life_mana_bars.getCenter().getX()+101
    life_y = life_mana_bars.getCenter().getY()-7
 
    test_x = (start_life_x + int((float(percent)/100) * (end_life_x - start_life_x)))   
    red = getPixelColorForHealer(test_x,life_y,"life")
        
    if red >= 200:
        return 0
    else:
        return 1

def manaTest(percent):

    start_mana_x = life_mana_bars.getCenter().getX()+9
    end_mana_x = life_mana_bars.getCenter().getX()+101
    mana_y = life_mana_bars.getCenter().getY()+6
    
    test_x = (start_mana_x + int((float(percent)/100) * (end_mana_x - start_mana_x)))    
    blue = getPixelColorForHealer(test_x,mana_y,"mana")
    if blue >= 200:
        return 0
    else:
        return 1


def startHealingThread():
    healer_thread = threading.Thread(target=healingThread, args = (0,))
    if healer_thread.isAlive() == False:
        print "Starting healing thread"
        healer_thread.start()
    else: 
        print "[ERROR] Healing thread already running"

        
#targeting thread
def attackingThread(arg):
    
    while running == 1: 
    
        for atk in targeting:

            if in_battle == 1:
    
                if game_region.exists(no_mana_text,0):
                    log("Not enough mana to cast attack spell")
                    continue

                if countTargets(atk[2]) < atk[2]: 
                    #log("Not enough targets to cast "+str(atk[0]))
                    continue
                                
                if validate_hotkey(atk[3],atk[5],atk[4]) == 1:
                    log("Casting "+atk[0])
                    if atk[1] in function_keys: 
                        type(function_keys_dict[atk[1]])
                    else:
                        type(atk[1])
                    atk[5] = datetime.now()
                    if "exeta" in atk[0]: sleep(0)
                    else: sleep(2)

            else: break    
    
    else: print "Ending attacking thread"

def startAttackingThread():
    spell_cast_thread = threading.Thread(target=attackingThread, args = (0,))
    if spell_cast_thread.isAlive() == False:
        print "Starting attacking thread"
        spell_cast_thread.start()
    else: 
        print "[ERROR] Attacking thread already running"

#CHARACTER STATUS AND DEBUFFS

def persistentActions():
    log("Checking persistent actions")
    #if equip_region.exists(paralyse_icon,0): type(haste)
    #if equip_region.exists(food_icon,0): type(food)
    #if equip_region.exists(poison_icon,0): type(cure_poison)
    if (equip_ring == 1 and equip_region.exists(no_ring_img,0)): type(ring)
    if (equip_amulet == 1 and equip_region.exists(no_amulet_img,0)): type (amulet)
    else:return

#DROP ITEMS ON THE GROUND

def dropVials():
    log("Searching for empty vials")
    try:
        dropItemToFeet(Pattern("small_flask.png").exact(),"small empty flask")
        dropItemToFeet(Pattern("strong_flask.png").exact(),"strong empty flask")
        dropItemToFeet(Pattern("great_flask.png").exact(),"great empty flask")
    except: log("ERROR dropping vials")

def dropListOfItems(wpList):
    checkBattleList()
    try:
        for index,tuple in enumerate(wpList[1]):
            sprite = tuple[0]
            name   = tuple[1]
            if exists(sprite,0): dropItemToFeet(sprite,name)
    except: print "ERROR droping items"

def dropItemToFeet(sprite,name):
    if exists(sprite,0):
        imageCount = len(list([x for x in findAll(sprite)]))
        for i in range(imageCount):
            log("Dropping "+name+" "+str(i+1)+"/"+str(imageCount))
            dragDrop(sprite, Location(gr_center_x,gr_center_y))
            wait(0.5)
    else: return
    
#DEPOSIT ITEMS ON DEPOT

def depositItem(container,list_of_items):
    log("Under construction")
    #1) FIND EMPTY FLOOR
    #2) FIND LOCKER (N, S, W, E)
    #3) CLICK IT
    #4) DEPOSIT ITEMS ACCORDINGLY TO USER SPECIFICATIONS
    return

#TALK TO NPC AND BUY ITEMS ON TRADE

def talkToNPC(wpList):
    try: 
        log("Talking to NPC...")
        click(Pattern("chatoff.png").exact());wait(2)
        dialogs = wpList[1].split(';')
        for dialog in dialogs:
            type(dialog)
            type(Key.ENTER)
            wait(1.5)
        click(Pattern("chaton.png").exact())
    except: log("ERROR Talking to NPC")

def buyItem(item,qtd):
    npc_trade_start = find("npc0.png")
    nts_x = npc_trade_start.getX()
    nts_y = npc_trade_start.getY()
    
    npc_trade_end = find("npc1.png")
    nte_x = npc_trade_end.getX()
    nte_y = npc_trade_end.getBottomRight().getY()

    npc_trade_region = Region(
            nts_x,
            nts_y,
            180,
            (nte_y-nts_y)
    )
    
    #npc_trade_region.highlight(1)
    log("Browsing through npc items")
    while not exists(item,0): npc_trade_region.click("npc2.png")
    else: npc_trade_region.click(item)

    qtd_bar_region = Region(
            npc_trade_end.getTopLeft().getX(),
            npc_trade_end.getTopLeft().getY(),
            130,
            20
    )

    hqtd = 1
    if qtd > 100: 
        hqtd = int(qtd/100)
        qtd = 100
    log("Buying "+str(hqtd)+"x "+str(qtd)+" items")
    more_icon = qtd_bar_region.find(Pattern("npc3.png").exact())
    for i in range(qtd): more_icon.click()
    for i in range(hqtd): npc_trade_region.click("npc4.png")

#DUST/SKIN CREATURE CORPSES
def skinCreatureCorpse(list_of_corpses):
    log("Under construction")
    #1) FIND CORPSE ON SCREEN
    #2) CLICK IT WITH TOOL
    #3) REPEAT IF THERE IS ANOTHER CORPSE
    return

#SCRIPT SELECTION

##The code snippet below should be easier for user to handle
##and also removes hard code, but first must be 
##evaluated if increases initialization time

#script_dict = {}
#script_file = open("/Users/GabrielMargonato/Downloads/SIKULI/BOT.sikuli/available_scripts.txt")
#for line in script_file:
#    key,value = line.rstrip('\n').split(":")
#    script_dict[key] = value

def scriptSelector():
    script_dict = {
        "Rook Mino Hell" : "mino_hell",
        "Kazordoon Drillworms Left" : "kazz_drillworm"    
    }
    
    list_keys = []
    for key,value in script_dict.items():
        list_keys.append(key)

    user_selection = select("Please select a script from the list",
            "Available Scripts", 
            options = list_keys, 
            default = list_keys[0])

    global selected_script   
    selected_script = script_dict[user_selection]
    log("Selected Script: "+selected_script)

    global imported_script
    
    global vocation      
    global loot_type    
    global lure_mode
    global equip_ring    
    global equip_amulet  
    global drop_vials    
    global dust_skin
    global use_haste
    
    global healing
    global targeting

    global wp
    global last_hunt_wp
    global last_leave_wp
    global last_go_hunt_wp

    global leave_conditions
    
    #imports the script that will be executed on this session
    imported_script = importlib.import_module(selected_script)
    
    vocation      = imported_script.vocation
    loot_type     = imported_script.loot_type 
    lure_mode     = imported_script.lure_mode  
    equip_ring    = imported_script.equip_ring
    equip_amulet  = imported_script.equip_amulet
    drop_vials    = imported_script.drop_vials
    dust_skin     = imported_script.dust_skin
    use_haste     = imported_script.use_haste

    #waypoints
    last_go_hunt_wp = len(imported_script.label_go_hunt)
    last_hunt_wp    = len(imported_script.label_hunt)
    last_leave_wp   = len(imported_script.label_leave)

    #leave hunt conditions list
    leave_conditions = imported_script.leave_conditions
    
    #imports healing list
    healing   = imported_script.healing
    #if healing list exists:
    if healing: userHealInputParser(healing)
    
    #imports targeting list
    targeting = imported_script.targeting
    #if targetings list exists:
    if targeting: userAtkInputParser(targeting)

heal_dict = {
    "exura ico":        ["heal_spell",1],
    "exura gran ico":   ["heal_spell",600],
    "exura med ico":    ["heal_spell",1],
    "exura infir ico":  ["heal_spell",1],
    "utura":            ["heal_spell",60],
    "utura gran":       ["heal_spell",60]
}
        
def userHealInputParser(healing):
    #  0    1      2     3    4   5   6
    #[type,name,percent,htk|group,cd,LTU]
    for heal in healing:
        if ("potion" in heal[1]) or ("rune" in heal[1]):           
            heal.append("obj")
            if "potion" in heal[1]: heal.append(1)
            else: heal.append(2)
            heal.append(datetime.now())
        else:
            dict_aux = heal_dict[heal[1]]
            heal.append(dict_aux[0])
            heal.append(dict_aux[1])
            heal.append(datetime.now())
    print "Healing parsed"
    
atk_spells_dict = {
    "exori":            ["atk_spell",4],
    "exori gran":       ["atk_spell",6],
    "exori gran ico":   ["atk_spell",30],
    "exori hur":        ["atk_spell",6],
    "exori ico":        ["atk_spell",6],
    "exori mas":        ["atk_spell",8],
    "exori min":        ["atk_spell",6],
    "exeta res":        ["atk_spell",2],
    "exeta amp res":    ["atk_spell",2]
}    
    
def userAtkInputParser(targeting):
    #  0    1      2         3    4  5
    #[name,htk,min_targets|group,cd,LTU]
    for atk in targeting:
        if "rune" in atk[0]:
            atk.append("obj")
            atk.append(2)
            atk.append(datetime.now())
        else:
            dict_aux = atk_spells_dict[atk[0]]
            atk.append(dict_aux[0])
            atk.append(dict_aux[1])
            atk.append(datetime.now())
    print "Targeting parsed"  
        
#CONSOLE
def startConsole():
    global frame_x
    global frame_y
    try:
        localchat = find(local_chat_text)
        frame_x = (localchat.getX()) - 22 
        frame_y = (localchat.getY()) + 22
    except: 
        frame_x = 0
        frame_y = 43
    if console_type == "complex": createComplexConsole()
    else: createSimpleConsole()

def pauseExecution(event):
    global running
    running = 0
    quitButton.setEnabled(False)
    #quitButton.setText("RESUME")
    #quitButton.setForeground(Color.GREEN)
    if console_type != "complex": frame.dispose()

#Complex
def createComplexConsole():
    global frame
    
    #structure
    frame = JFrame("[BETA] Game Master\'s Bot - Console")
    frame.setBounds(frame_x,frame_y,600,130)
    frame.contentPane.layout = FlowLayout()
    
    #behavior
    frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE)
    frame.setResizable(False)
    frame.setAlwaysOnTop(True)
    
    #Buttons
    global quitButton
    quitButton = JButton("STOP", actionPerformed = pauseExecution)
    quitButton.setForeground(Color.RED)
    quitButton.setPreferredSize(Dimension(100,100))
    frame.contentPane.add(quitButton)
    
    #Text
    global textArea
    textArea = JTextArea(6,38)
    textArea.setEditable(False)
    frame.contentPane.add(textArea)
    scrollPane = JScrollPane(textArea, JScrollPane.VERTICAL_SCROLLBAR_ALWAYS, JScrollPane.HORIZONTAL_SCROLLBAR_AS_NEEDED)
    frame.contentPane.add(scrollPane)
    
    #Show
    frame.pack()
    frame.setVisible(True)

#Simple
def createSimpleConsole():
    global frame
    
    #structure
    frame = JFrame("[BETA] GameMaster Bot - Console")
    frame.setBounds(frame_x,frame_y,560,50)
    
    #behavior
    frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE)
    #frame.setUndecorated(True)
    frame.setAlwaysOnTop(True)

    #text
    global messageLOG
    messageLOG = JLabel("")
    frame.add(messageLOG,BorderLayout.CENTER)
    
    #Button
    global quitButton
    quitButton = JButton("STOP", actionPerformed = pauseExecution)
    quitButton.setForeground(Color.RED)
    frame.add(quitButton,BorderLayout.WEST)

    #Show
    frame.setVisible(True)

#receives a message and print it
def log(message):
    if console_type == "simple":
        messageLOG.setText(str(datetime.now().strftime(" %H:%M:%S.%f")[:-4])+" - "+str(message)+"\n")
    else:
        if textArea.getLineCount() <= 500:
            textArea.append(str(datetime.now().strftime("%H:%M:%S.%f")[:-4])+" - "+str(message)+"\n")
            textArea.setCaretPosition(textArea.getDocument().getLength())
        else: textArea.setText("Reseting log (more than 500 lines) \n")

startConsole()
log("Welcome to GameMaster\'s Bot!")

#START OF EXECUTION
game_region.highlight(0.5,"green") #expendable step - just to show the user

#sets running variable to 1
running = 0

#1) Asks user which script will be executed
scriptSelector()

#2) Asks user the starting label
label = select("Please select a starting point","Available Starting Points", options = ("go_hunt","hunt","leave"), default = "go_hunt")

#3) Asks user at which waypoint
if label == "go_hunt":
    available_wps = list(range(1,last_go_hunt_wp+1))
    
if label == "hunt":
    available_wps = list(range(1,last_hunt_wp+1))

if label == "leave":
    available_wps = list(range(1,last_leave_wp+1))

list_of_wps = map(str, available_wps)
wp_str = select("Choose a starting waypoint",label, list_of_wps, default = 0)
wp = int(wp_str)

#4) generates an ID for this session
session_id = str(datetime.now().strftime("%d%m%Y%H%M"))
log("Session ID: "+str(session_id))
log("Starting at "+label+" waypoint "+str(wp))
#log("[ATTENTION] Walk interval is set to "+str(walk_interval)+" second(s)")

#5) focus on tibia client
App.focus("Tibia")

#show ping on screen
if not exists(ping_icon,0): type(Key.F8, KeyModifier.ALT)

#6) Calculates regions based on game screen elements    
#GAME REGION INFORMATIONS
#center
gr_center_x = game_region.getCenter().getX()
gr_center_y = game_region.getCenter().getY()

#top left corner
gr_tlc_x = game_region.getTopLeft().getX()
gr_tlc_y = game_region.getTopLeft().getY()

#top right corner
gr_trc_x = game_region.getTopRight().getX()
gr_trc_y = game_region.getTopRight().getY()

#bottom left corner
gr_blc_x = game_region.getBottomLeft().getX()
gr_blc_y = game_region.getBottomLeft().getY()

#bottom right corner
gr_brc_x = game_region.getBottomRight().getX()
gr_brc_y = game_region.getBottomRight().getY()

multiplier = (gr_center_y - gr_tlc_y) / 5

# x1,y1 | x2,y1 | x3,y1
# x1,y2 | x2,y2 | x3,y2
# x1,y3 | x2,y3 | x3,y3

x1 = gr_center_x - multiplier
x2 = gr_center_x
x3 = gr_center_x + multiplier

y1 = gr_center_y - multiplier
y2 = gr_center_y
y3 = gr_center_y + multiplier

pos_dict = {
    "NW": Location(x1,y1),
    "N":  Location(x2,y1),
    "NE": Location(x3,y1),
    "W":  Location(x1,y2),
    "C":  Location(x2,y2),
    "E":  Location(x3,y2),
    "SW": Location(x1,y3),
    "S":  Location(x2,y3),
    "SE": Location(x3,y3)
}

#Battle list region
try: battlelist = find(battle_list_text)
except: raise Exception("Battle list not found")
bl_tlc_x = battlelist.getTopLeft().getX()
bl_tlc_y = battlelist.getTopLeft().getY()
bl_slot1_x = bl_tlc_x + 26
bl_slot1_y = bl_tlc_y + 33
battlelist_region = Region(bl_tlc_x,bl_tlc_y,40,200)

#Life and mana bars region
try: life_mana_bars = find(life_mana_img)
except: raise Exception("Life bars not found!")

#Equipments region
try: equip_coords = find(store_purse_img)
except: raise Exception("Equipment not found!")
equip_coords_x = equip_coords.getTopRight().getX()+5
equip_coords_y = equip_coords.getTopRight().getY()
equip_region = Region((equip_coords_x-115),equip_coords_y,110,163)

#Minimap region
try: minimap_area = find(minimap_ref_img)
except: raise Exception ("Minimap not found!")
mma_aux_x = minimap_area.getTopLeft().getX()
mma_aux_y = minimap_area.getTopLeft().getY()
minimap_area_x = mma_aux_x - 115
minimap_area_y = mma_aux_y - 49

try:
    sub_zoom = find(sub_zoom_img)
    add_zoom = find(add_zoom_img)
except: raise Exception ("Zoom buttons not found!")
    
#MAIN

#sets running variable to 1
running = 1

#starts healing and attacking threads (if vocation > 0)
startHealingThread()
if vocation > 0: startAttackingThread()
print " "

if label == "hunt":
    checkBattleList()

while running == 1:

    encounter = -1
    if label == "hunt": 
        if lure_mode == 1: checkBattleList()
        persistentActions()
        
    waypointManager()

    #gc.collect()

else: 
    #popup("END")
    log("END - you may close this window now")
