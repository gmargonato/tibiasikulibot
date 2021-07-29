#Gamemaster's Bot BETA

#library imports
import os
import gc
import subprocess
import re
import math
import importlib
import json
import threading
import shutil
import potions

from datetime import *
from random import *
from javax.swing import JFrame, JButton, JLabel, JScrollPane, JTextArea, JPanel, JButton
from java.awt import BorderLayout,GridLayout,GridBagConstraints,GridBagLayout,FlowLayout,Dimension,Robot, Color
from sikuli import *

#basic settings
Settings.ObserveScanRate = 10
Settings.MoveMouseDelay = 0
Settings.ActionLogs = 0
Settings.InfoLogs = 0
Settings.DebugLogs = 0

############################################################
 ######   #######  ##    ## ######## ####  ######    ######  
##    ## ##     ## ###   ## ##        ##  ##    ##  ##    ## 
##       ##     ## ####  ## ##        ##  ##        ##       
##       ##     ## ## ## ## ######    ##  ##   ####  ######  
##       ##     ## ##  #### ##        ##  ##    ##        ## 
##    ## ##     ## ##   ### ##        ##  ##    ##  ##    ## 
 ######   #######  ##    ## ##       ####  ######    ######  
############################################################

#options: simple/complex
console = "complex"

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
exana_pox = "i"
haste     = "b"

#defines game region
game_region = Region(223,121,483,353)

##########################################
########  #### ##     ## ######## ##       
##     ##  ##   ##   ##  ##       ##       
##     ##  ##    ## ##   ##       ##       
########   ##     ###    ######   ##       
##         ##    ## ##   ##       ##       
##         ##   ##   ##  ##       ##       
##        #### ##     ## ######## ########
##########################################

def pixelColor(posX,posY):   
    pixel = Robot().getPixelColor(posX,posY)
    r = pixel.getRed()
    g = pixel.getGreen() 
    b = pixel.getBlue() 
    color = '{:02x}{:02x}{:02x}'.format(r,g,b)
    return color

def healerColor(posX,posY,id):

    pixel = Robot().getPixelColor(posX,posY)
    if   id == "life": return pixel.getRed()
    elif id == "mana": return pixel.getBlue() 
    else: return 0

###########################################################
##        #######   ######       #######  ######## ######## 
##       ##     ## ##    ##     ##     ## ##       ##       
##       ##     ## ##           ##     ## ##       ##       
##       ##     ## ##   ####    ##     ## ######   ######   
##       ##     ## ##    ##     ##     ## ##       ##       
##       ##     ## ##    ##     ##     ## ##       ##       
########  #######   ######       #######  ##       ##       
###########################################################

def logoff_function():
    
    if equip_region.exists("battleon.png"):
        log("Could not logoff, waiting 10 seconds...")
        check_battle_list()
        wait(10)
        log("Trying to logoff again")
        logoff_function()
        
    else:
        myOS = Settings.getOS()
        if myOS == OS.MAC:        
            type("3", KeyModifier.CMD + KeyModifier.SHIFT)
            type("l", KeyModifier.CMD)
        else:
           type("l", KeyModifier.CTRL) 
        log("[END OF EXECUTION]")
        #closeFrame(0)
        global running
        running = 0

########################################################################
##      ##    ###    ##    ## ########   #######  #### ##    ## ######## 
##  ##  ##   ## ##    ##  ##  ##     ## ##     ##  ##  ###   ##    ##    
##  ##  ##  ##   ##    ####   ##     ## ##     ##  ##  ####  ##    ##    
##  ##  ## ##     ##    ##    ########  ##     ##  ##  ## ## ##    ##    
##  ##  ## #########    ##    ##        ##     ##  ##  ##  ####    ##    
##  ##  ## ##     ##    ##    ##        ##     ##  ##  ##   ###    ##    
 ###  ###  ##     ##    ##    ##         #######  #### ##    ##    ##    
########################################################################
current_zoom = -1

#controls waypoints
def waypointer():

    global wp
    global label
    
    if label == "go_hunt":  wpList = imported_script.label_go_hunt(wp)
    if label == "hunt":     wpList = imported_script.label_hunt(wp)
    if label == "leave":    wpList = imported_script.label_leave(wp)
    if label == "go_refil": wpList = imported_script.label_go_refil(wp)
    
    #list of possible waypoint actions
    if   wpList[0] == "walk" and running == 1: walk(wpList)
    elif wpList[0] in ("rope","ladder","shovel"): waypoint_action(wpList[0])
    elif wpList[0] == "drop": drop_item(wpList)
    elif wpList[0] == "talk": talk_to_npc(wpList)
    elif wpList[0] == "attack": check_battle_list()
    elif wpList[0] == "deposit": deposit_item(wpList[1])
    elif wpList[0] == "go_refil": label = "go_refil";wp = 0
    elif wpList[0] == "refil": buy_item(wpList[1],wpList[2])
    elif wpList[0] == "reset": reset_run()
    elif wpList[0] == "pass": pass
    else: print "WARNING: error on waypoint",wp,":",wpList[0]
       
    #Arrived at waypoint
    if label == "go_hunt" and wp >= last_go_hunt_wp:
        log("Setting label to hunt")
        label = "hunt"
        wp = 1
        
    elif label == "hunt" and wp >= last_hunt_wp:
        if drop_vials > 0 and running == 1: 
            check_battle_list()
            drop_item_vial()
        
        log("Checking conditions to leave hunt...")
        for condition in leave_conditions:
            index = (leave_conditions.index(condition)) + 1
            log("Condition "+str(index)+": "+condition[0])
            label = check_leave_conditions(condition[0],condition[1])
            if label == "leave": break #if a leave condition is found, shoul not check for another

        #set next wp back to 1         
        wp = 1
        
    elif label == "leave" and wp >= last_leave_wp:
        logoff_function()
    
    else: wp+=1


def check_leave_conditions(name,param):
    
    #check if potion
    if "potion" in name:
        
        try:
            while param >= 0:
                if name == "small health potion": img_ref = potions.small_health_potion_dict[param]
                if name == "mana potion":         img_ref = potions.mana_potion_dict[param]
                if name == "strong mana potion":  img_ref = potions.strong_mana_potion_dict[param]  
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
        return check_time(param[0],param[1])
        
    #if not a potion, use variable param as pattern
    else: 
        if exists(param,0): return "leave"
        else: return "hunt"

#check current machine time
def check_time(interval_1,interval_2):

    current_time = datetime.now().strftime("%H:%M") 
    print "Current time:",current_time
    if current_time >= interval_1 and current_time <= interval_2:
        return "leave"
    else:
        return "hunt"        
        
        
def walk(wpList):
#wpList = [0:action, 1:img ,2:zoom, 3:atk]   

    global current_zoom
    
    if wpList[2] != current_zoom: 
        
        for i in range(0,3):
            click(Location(sub_zoom.getX(),sub_zoom.getY()))
    
        for i in range(0,wpList[2]):
            click(Location(add_zoom.getX(),add_zoom.getY()))
    
        #update current_zoom to new value
        current_zoom = wpList[2]
        
    else: pass

    log("Walking to "+label+" waypoint "+str(wp))
    try:
        
        #click the match on screen
        click(wpList[1])

        #check if should cast haste
        if not use_haste: pass
        elif (label == "go_hunt" and "go_hunt" in use_haste) or (label == "hunt" and "hunt" in use_haste) or (label == "leave" and "leave" in use_haste): type(haste)
        else: pass

        #check if the character is moving or not
        check_is_walking(wpList)
        
    except: log("Could not find waypoint "+label+" "+str(wp))
    return
    
def check_is_walking(wpList):
#wpList = [0:action, 1:img ,2:zoom, 3:atk]   

    global encounter
    time_stopped = 0
    
    while time_stopped != walk_interval:

        if encounter == 0: return
        
        minimap_region = Region(minimap_area_x,minimap_area_y,110,115)
        minimap_region.onChange(1,changeHandler)
        minimap_region.somethingChanged = False
        minimap_region.observe(1)
        
        #if enters here, means char is still walking
        if minimap_region.somethingChanged:
            
            time_stopped = 0
            
            #while is walking and paralysed, use haste
            while equip_region.exists("paralysed.png",0): 
                type(haste)
                wait(0.5)
            
            #if going or leaving hunt, and no way (possibly trapped), attack
            if (wpList[0] == "go_hunt" or wpList[0] == "leave") and game_region.exists(Pattern("thereisnoway.png").exact(),0):
                log("Possibly trapped")
                type(Key.SPACE)
                wait(0.3)
                battlelist_region.waitVanish("bl_target.png",10)
                walk(wpList)
                    
            if wpList[3] > 0: 
                if (not game_region.exists(Pattern("thereisnoway.png").exact(),0)) and (count_targets(wpList[3]) >= wpList[3]): 
                    type(Key.ESC)
                    wait(0.3)
                    check_battle_list()
                    if running == 1: walk(wpList)
                else: wait(1)
            
        #if nothing changes on the screen for some time, add 1 to stopped timer
        if not minimap_region.somethingChanged:
            time_stopped+=1
            log("Walking "+str(time_stopped)+"/"+str(walk_interval))

    else: 
        log("Arrived at waypoint")
        encounter = 0
        return


#function to verify if something is changing on screen
def changeHandler(event):
    event.region.somethingChanged = True
    event.region.stopObserver()

def waypoint_action(wp_action): 
    if wp_action == "rope":
        type(rope)
        click(Location(gr_center_x,gr_center_y))
        log("Using rope")
        
    if wp_action == "ladder":
        click(Location(gr_center_x,gr_center_y))
        log("Using ladder")
        
    if wp_action == "shovel":
        type(shovel)
        click(Location(gr_center_x,gr_center_y))
        log("Using shovel")    

    wait(1)
    return

def reset_run():
    global wp
    global label

    for condition in leave_conditions:
        index = (leave_conditions.index(condition)) + 1
        next_label = check_leave_conditions(condition[0],condition[1])
        if next_label == "leave": break #if a leave condition is found, shoul not check for another

    if next_label == "hunt":
        log("Restarting hunt from the beginning")
        label = "go_hunt"
        wp = 0
    else:
        label = "leave"
        
#######################################################
########     ###    ######## ######## ##       ######## 
##     ##   ## ##      ##       ##    ##       ##       
##     ##  ##   ##     ##       ##    ##       ##       
########  ##     ##    ##       ##    ##       ######   
##     ## #########    ##       ##    ##       ##       
##     ## ##     ##    ##       ##    ##       ##       
########  ##     ##    ##       ##    ######## ######## 
#######################################################
in_battle = 0
        
def check_battle_list():

    global encounter
    global in_battle
    in_battle = 0

    if running == 1 and pixelColor(bl_slot1_x,bl_slot1_y) == "000000": 
   
        log("Attacking mob...")
        type(Key.SPACE)
        wait(0.3)
        encounter = 1

        #in case there is no way to the mob
        if check_no_way == 1: 
            if game_region.exists(Pattern("thereisnoway.png").exact(),0):
                log("There is no way")
                type(Key.ESC)
                if loot_type == 3: loot_around(1)
                return

        #flag in_battle is used to start/end casting spells
        in_battle = 1
        battlelist_region.waitVanish("bl_target.png",30)    
        in_battle = 0
        
        if game_region.exists("valuable_loot.png",0): loot_around(2)
        if loot_type == 1 and label == "hunt": loot_around(1)
        check_battle_list()

    elif running == 0: return    
    else: 
        log("Battle list is clear")
        if drop_vials == 2: drop_item_vial()
        if encounter == 1 and loot_type == 3: loot_around(1)
        if dust_skin == 1 and label == "hunt":
            try: dust_creature_corpse(imported_script.corpses)
            except: pass
        return
 
#####################################
##        #######   #######  ######## 
##       ##     ## ##     ##    ##    
##       ##     ## ##     ##    ##    
##       ##     ## ##     ##    ##    
##       ##     ## ##     ##    ##    
##       ##     ## ##     ##    ##    
########  #######   #######     ##    
#####################################

#loot_type = 0 -> ignore loot
#loot_type = 1 -> loot everything
#loot_type = 2 -> loot only valuable
#loot_type = 3 -> loot only after clearing the battle list (best used along lure mode)

def loot_around(times):
    log("Looting around char ("+str(times)+")")
    for i in range(times):
        click(Location(x1,y1),8)    
        click(Location(x2,y1),8)
        click(Location(x3,y1),8)
        click(Location(x1,y2),8)  
        click(Location(x2,y2),8)
        click(Location(x3,y2),8)
        click(Location(x1,y3),8)    
        click(Location(x2,y3),8)
        click(Location(x3,y3),8)

#######################################################
##     ##  #######  ######## ##    ## ######## ##    ## 
##     ## ##     ##    ##    ##   ##  ##        ##  ##  
##     ## ##     ##    ##    ##  ##   ##         ####   
######### ##     ##    ##    #####    ######      ##    
##     ## ##     ##    ##    ##  ##   ##          ##    
##     ## ##     ##    ##    ##   ##  ##          ##    
##     ##  #######     ##    ##    ## ########    ##    
#######################################################
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

#####################################
##     ## ########    ###    ##      
##     ## ##         ## ##   ##      
##     ## ##        ##   ##  ##      
######### ######   ##     ## ##      
##     ## ##       ######### ##      
##     ## ##       ##     ## ##      
##     ## ######## ##     ## ########
#####################################

#Healing thread
def healing_thread(arg):

    while running == 1:
                       
        for heal in healing:

            if heal[0] == "hp": shouldHeal = life_test(heal[2])
            else: shouldHeal = mana_test(heal[2])
                
            if shouldHeal == 1: 
                valid = validate_hotkey(heal[4],heal[6],heal[5])
                if valid == 1:  
                    log(heal[0]+" < " +str(heal[2])+"%: Using "+str(heal[1]))
                    type(heal[3])
                    heal[6] = datetime.now()
                    
    else: print "Ending healing thread" 
                
def life_test(percent):

    start_life_x = life_mana_bars.getCenter().getX()+9
    end_life_x = life_mana_bars.getCenter().getX()+101
    life_y = life_mana_bars.getCenter().getY()-7
 
    test_x = (start_life_x + int((float(percent)/100) * (end_life_x - start_life_x)))   
    red = healerColor(test_x,life_y,"life")
        
    if red >= 200:
        return 0
    else:
        return 1

def mana_test(percent):

    start_mana_x = life_mana_bars.getCenter().getX()+9
    end_mana_x = life_mana_bars.getCenter().getX()+101
    mana_y = life_mana_bars.getCenter().getY()+6
    
    test_x = (start_mana_x + int((float(percent)/100) * (end_mana_x - start_mana_x)))    
    blue = healerColor(test_x,mana_y,"mana")
    if blue >= 200:
        return 0
    else:
        return 1


def start_healing_thread():
    healer_thread = threading.Thread(target=healing_thread, args = (0,))
    if healer_thread.isAlive() == False:
        print "Starting healing thread"
        healer_thread.start()
    else: 
        print "[ERROR] Healing thread already running"

########################################################
########    ###    ########   ######   ######## ########
   ##      ## ##   ##     ## ##    ##  ##          ##   
   ##     ##   ##  ##     ## ##        ##          ##   
   ##    ##     ## ########  ##   #### ######      ##   
   ##    ######### ##   ##   ##    ##  ##          ##   
   ##    ##     ## ##    ##  ##    ##  ##          ##   
   ##    ##     ## ##     ##  ######   ########    ##   
########################################################

def count_targets(slots):

    slot = bl_slot1_y
    num_targets = 0
     
    #log("Checking "+str(slots)+" slot(s)")
    #cycle trought battle list slots
    for i in range(slots):
        #log("\t"+"slot "+str((i+1))+"/"+str(slots))
        if pixelColor(bl_slot1_x,slot) == "000000": num_targets+=1
        slot += 22

    return num_targets

#targeting thread
def attacking_thread(arg):
    
    while running == 1: 
    
        for atk in targeting:

            #if battlelist_region.exists("bl_target.png",0):
            if in_battle == 1:
    
                if game_region.exists(Pattern("noenoughmana.png").similar(0.90),0):
                    log("Not enough mana to cast attack spell")
                    continue

                if count_targets(atk[2]) < atk[2]: 
                    #log("Not enough targets to cast "+str(atk[0]))
                    continue
                                
                if validate_hotkey(atk[3],atk[5],atk[4]) == 1:
                    log("Casting "+atk[0])
                    type(atk[1])
                    atk[5] = datetime.now()
                    if "exeta" in atk[0]: sleep(0)
                    else: sleep(2)

            else: break    
    
    else: print "Ending attacking thread"

def start_attacking_thread():
    spell_cast_thread = threading.Thread(target=attacking_thread, args = (0,))
    if spell_cast_thread.isAlive() == False:
        print "Starting attacking thread"
        spell_cast_thread.start()
    else: 
        print "[ERROR] Attacking thread already running"

#################################################################
########  ######## ########  ##     ## ######## ########  ######  
##     ## ##       ##     ## ##     ## ##       ##       ##    ## 
##     ## ##       ##     ## ##     ## ##       ##       ##       
##     ## ######   ########  ##     ## ######   ######    ######  
##     ## ##       ##     ## ##     ## ##       ##             ## 
##     ## ##       ##     ## ##     ## ##       ##       ##    ## 
########  ######## ########   #######  ##       ##        ######  
#################################################################

def check_debuffs():
    log("Checking status and debuffs")
    #while equip_region.exists("paralysed.png",0): type(haste)
    #if equip_region.exists("food.png",0): type(food)
    #while equip_region.exists("poison.png",0): type(exana_pox)
    if (equip_ring == 1 and equip_region.exists("ring.png",0)): type(ring)
    if (equip_amulet == 1 and equip_region.exists("amulet.png",0)): type (amulet)
    else:return

#######################################
########  ########   #######  ########  
##     ## ##     ## ##     ## ##     ## 
##     ## ##     ## ##     ## ##     ## 
##     ## ########  ##     ## ########  
##     ## ##   ##   ##     ## ##        
##     ## ##    ##  ##     ## ##        
########  ##     ##  #######  ##        
#######################################

def drop_item_vial():
    log("Searching for vials to drop...")
    try:
        drop_item_to_sqm(Pattern("small_flask.png").exact(),"small empty flask")
        drop_item_to_sqm(Pattern("strong_flask.png").exact(),"strong empty flask")
        drop_item_to_sqm(Pattern("great_flask.png").exact(),"great empty flask")
    except: log("ERROR dropping vials")

def drop_item(wpList):
    check_battle_list()
    try:
        for index,tuple in enumerate(wpList[1]):
            sprite = tuple[0]
            name   = tuple[1]
            if exists(sprite,0): drop_item_to_sqm(sprite,name)
    except: print "ERROR droping items"

def drop_item_to_sqm(sprite,name):
    if exists(sprite,0):
        imageCount = len(list([x for x in findAll(sprite)]))
        for i in range(imageCount):
            log("Dropping "+name+" "+str(i+1)+"/"+str(imageCount))
            dragDrop(sprite, Location(gr_center_x,gr_center_y))
            wait(0.5)
    else: return
    
################################################################################
########  ######## ########   #######   ######  #### ######## ######## ########  
##     ## ##       ##     ## ##     ## ##    ##  ##     ##    ##       ##     ## 
##     ## ##       ##     ## ##     ## ##        ##     ##    ##       ##     ## 
##     ## ######   ########  ##     ##  ######   ##     ##    ######   ########  
##     ## ##       ##        ##     ##       ##  ##     ##    ##       ##   ##   
##     ## ##       ##        ##     ## ##    ##  ##     ##    ##       ##    ##  
########  ######## ##         #######   ######  ####    ##    ######## ##     ## 
################################################################################

#get match closest to mouse location
def by_nearest(match):
    refLocation = Env.getMouseLocation() 
    x = math.fabs(match.getCenter().x - refLocation.x)
    y = math.fabs(match.getCenter().y - refLocation.y)
    distance = int(math.sqrt(x * x + y * y))
    return distance

def deposit_item(list_of_items):
    try:
        log("Walking to empty depot tile")
        click(Pattern("depot0.png").similar(0.35))
        wait(walk_interval)
    except: 
        log("Could not find an empty depot tile")
        return
    
    if exists("depot1.png",0): dp_img = "depot1.png"
    elif exists("depot2.png",0): dp_img = "depot2.png"
    elif exists("depot3.png",0): dp_img = "depot3.png"
    else: 
        log("Could not find Locker")
        return

    hover(Location(x2,y2))    
    sortedMatches = sorted(findAll(dp_img), key=by_nearest)
    click(sortedMatches[0])
    try:
        wait("depot4.png")
        click("depot4.png")
        log("Depositing items...")
        for item in list_of_items: 
            try:
                while exists(item): dragDrop(find(item),"depot5.png")
            except: continue
        log("... Items deposited")
        
    except: 
        log("ERROR: Could not deposit one or more items")
        return

#####################################################################
########  ######## ######## #### ##       ##       ######## ########  
##     ## ##       ##        ##  ##       ##       ##       ##     ## 
##     ## ##       ##        ##  ##       ##       ##       ##     ## 
########  ######   ######    ##  ##       ##       ######   ########  
##   ##   ##       ##        ##  ##       ##       ##       ##   ##   
##    ##  ##       ##        ##  ##       ##       ##       ##    ##  
##     ## ######## ##       #### ######## ######## ######## ##     ## 
#####################################################################

def talk_to_npc(wpList):
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

def buy_item(item,qtd):
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

##############################################################################
########  ##     ##  ######  ########       ##  ######  ##    ## #### ##    ## 
##     ## ##     ## ##    ##    ##         ##  ##    ## ##   ##   ##  ###   ## 
##     ## ##     ## ##          ##        ##   ##       ##  ##    ##  ####  ## 
##     ## ##     ##  ######     ##       ##     ######  #####     ##  ## ## ## 
##     ## ##     ##       ##    ##      ##           ## ##  ##    ##  ##  #### 
##     ## ##     ## ##    ##    ##     ##      ##    ## ##   ##   ##  ##   ### 
########   #######   ######     ##    ##        ######  ##    ## #### ##    ## 
##############################################################################

def dust_creature_corpse(list_of_corpses):
    log("Searching for corpses to dust/skin")
    return

#########################################################################
 ######  ######## ##       ########  ######  ########  #######  ########  
##    ## ##       ##       ##       ##    ##    ##    ##     ## ##     ## 
##       ##       ##       ##       ##          ##    ##     ## ##     ## 
 ######  ######   ##       ######   ##          ##    ##     ## ########  
      ## ##       ##       ##       ##          ##    ##     ## ##   ##   
##    ## ##       ##       ##       ##    ##    ##    ##     ## ##    ##  
 ######  ######## ######## ########  ######     ##     #######  ##     ##
#########################################################################
    
def script_selector_function():
    script_list = (
            "-nothing selected-",
            "Rook Mino Hell"
    )
    
    prompt = select("Please select a script from the list","Available Scripts", options = script_list, default = script_list[0])

    global selected_script
    
    if   prompt == script_list[1]:  selected_script = "mino_hell"
    else:
        popup("The selected script is not valid!")
        closeFrame(0)
        raise Exception("Invalid Script")
       
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
    last_hunt_wp    = imported_script.last_hunt_wp
    last_leave_wp   = imported_script.last_leave_wp
    last_go_hunt_wp = imported_script.last_go_hunt_wp

    #leave hunt conditions list
    leave_conditions = imported_script.leave_conditions
    
    #imports healing list
    healing   = imported_script.healing
    #if healing list exists:
    if healing: heal_parser(healing)
    
    #imports targeting list
    targeting = imported_script.targeting
    #if targetings list exists:
    if targeting: atk_parser(targeting)

def heal_parser(healing):
    #[type,name,percent,htk|group,cd,LTU]
    for heal in healing:
        #heal spells
        if heal[1] == "exura ico":          heal.append("heal_spell"); heal.append(1);    heal.append(datetime.now())
        elif heal[1] == "exura gran ico":   heal.append("heal_spell"); heal.append(600);  heal.append(datetime.now())
        elif heal[1] == "exura med ico":    heal.append("heal_spell"); heal.append(1);    heal.append(datetime.now())
        elif heal[1] == "exura infir ico":  heal.append("heal_spell"); heal.append(1);    heal.append(datetime.now())
        elif "utura" in heal[1]:            heal.append("heal_spell"); heal.append(60);   heal.append(datetime.now()) 
        elif "potion" in heal[1]:           heal.append("obj");        heal.append(1);    heal.append(datetime.now())
        else: popup("ERROR: "+str(heal[1])+" not identified")
    print "Healing parsed"
    
def atk_parser(targeting):
    #[name,htk,min_targets|group,cd,LTU]
    for atk in targeting:
        #knight spells
        if atk[0] == "exori":            atk.append("atk_spell"); atk.append(4);  atk.append(datetime.now())
        elif atk[0] == "exori gran":     atk.append("atk_spell"); atk.append(6);  atk.append(datetime.now())
        elif atk[0] == "exori gran ico": atk.append("atk_spell"); atk.append(30); atk.append(datetime.now())
        elif atk[0] == "exori hur":      atk.append("atk_spell"); atk.append(6);  atk.append(datetime.now())
        elif atk[0] == "exori ico":      atk.append("atk_spell"); atk.append(6);  atk.append(datetime.now())
        elif atk[0] == "exori mas":      atk.append("atk_spell"); atk.append(8);  atk.append(datetime.now())
        elif atk[0] == "exori min":      atk.append("atk_spell"); atk.append(6);  atk.append(datetime.now())
        elif "exeta" in atk[0]:          atk.append("atk_spell"); atk.append(2);  atk.append(datetime.now())
        elif "rune" in atk[0]:           atk.append("obj");       atk.append(2);  atk.append(datetime.now())
        else: popup("ERROR: "+str(atk[0])+" not identified")
    print "Targeting parsed"  
        
###############################################
######## ########     ###    ##     ## ######## 
##       ##     ##   ## ##   ###   ### ##       
##       ##     ##  ##   ##  #### #### ##       
######   ########  ##     ## ## ### ## ######   
##       ##   ##   ######### ##     ## ##       
##       ##    ##  ##     ## ##     ## ##       
##       ##     ## ##     ## ##     ## ######## 
###############################################

try: 
    localchat = find("local_chat.png")
    frame_x = (localchat.getX()) - 22 
    frame_y = (localchat.getY()) + 22
except: 
    frame_x = 0
    frame_y = 43

#receives a message and print it into jframe
def log(message):
    if console == "simple":
        messageLOG.setText(str(datetime.now().strftime(" %H:%M:%S.%f")[:-4])+" - "+str(message)+"\n")
    else:
        if textArea.getLineCount() <= 500:
            textArea.append(str(datetime.now().strftime("%H:%M:%S.%f")[:-4])+" - "+str(message)+"\n")
            textArea.setCaretPosition(textArea.getDocument().getLength())
        else: textArea.setText("Reseting console log (more than 500 lines) \n")
        
def closeFrame(event):
    global running
    running = 0
    quitButton.setEnabled(False)
    if console != "complex": frame.dispose()

#COMPLEX
def complex_console():
    global frame
    #generates frame
    frame = JFrame("[BETA] Game Master\'s Bot - Console Log")
    frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE)
    frame.setResizable(False)
    frame.setAlwaysOnTop(True)
    #frame.setBounds(8,545,600,130)
    frame.setBounds(frame_x,frame_y,600,130)
    frame.contentPane.layout = FlowLayout()
    
    #add QUIT button
    global quitButton
    quitButton = JButton("STOP", actionPerformed = closeFrame)
    quitButton.setForeground(Color.RED)
    quitButton.setPreferredSize(Dimension(100,100))
    frame.contentPane.add(quitButton)
    
    #add text message
    global textArea
    textArea = JTextArea(6,38)
    textArea.setEditable(False)
    frame.contentPane.add(textArea)
    scrollPane = JScrollPane(textArea, JScrollPane.VERTICAL_SCROLLBAR_ALWAYS, JScrollPane.HORIZONTAL_SCROLLBAR_AS_NEEDED)
    frame.contentPane.add(scrollPane)
    
    #show frame
    frame.pack()
    frame.setVisible(True)
    log("Welcome to Game Master\'s Bot!")

#SIMPLE
def simple_console():
    global frame
    frame = JFrame("[BETA] GameMaster Bot - Log")
    frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE)
    frame.setBounds(frame_x,frame_y,560,30)
    
    global messageLOG
    messageLOG = JLabel("")
    frame.add(messageLOG,BorderLayout.CENTER)
    
    global quitButton
    quitButton = JButton("QUIT", actionPerformed =closeFrame)
    quitButton.setForeground(Color.RED)
    frame.add(quitButton,BorderLayout.WEST)
    frame.setUndecorated(True)
    frame.setAlwaysOnTop(True)
    frame.setVisible(True)
    log("Welcome to GameMaster\'s Bot!")

if console == "simple": simple_console()
else: complex_console()

##############################################
 ######  ########    ###    ########  ######## 
##    ##    ##      ## ##   ##     ##    ##    
##          ##     ##   ##  ##     ##    ##    
 ######     ##    ##     ## ########     ##    
      ##    ##    ######### ##   ##      ##    
##    ##    ##    ##     ## ##    ##     ##    
 ######     ##    ##     ## ##     ##    ##    
##############################################

#execution starts here after hitting play/run
running = 0

#1) Asks user which script will be executed
script_selector_function()

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
#log("Session ID: "+str(session_id))
log("Starting at "+label+" waypoint "+str(wp))
#log("[ATTENTION] Walk interval is set to "+str(walk_interval)+" seconds")

#5) focus on tibia client and shows ping on game screen
App.focus("Tibia")
clientPID = App("Tibia").getPID()
if not exists(Pattern("ping.png").similar(0.50),0): type(Key.F8, KeyModifier.ALT)

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

screen_proportion = gr_brc_y/gr_trc_y
scp_perc = 10

# x1y1 , x2y1 , x3y1
# x1y2 , x2y2 , x3y2
# x1y3 , x2y3 , x3y3

x1 = gr_center_x - (screen_proportion*scp_perc)
x2 = gr_center_x
x3 = gr_center_x + (screen_proportion*scp_perc)

y1 = gr_center_y - (screen_proportion*scp_perc)
y2 = gr_center_y
y3 = gr_center_y + (screen_proportion*scp_perc)

#BATTLE LIST INFORMATIONS
try: battlelist = find(Pattern("battlelist.png").similar(0.75))
except: raise Exception("Battle list not found")

bl_tlc_x = battlelist.getTopLeft().getX()
bl_tlc_y = battlelist.getTopLeft().getY()

bl_slot1_x = bl_tlc_x + 26
bl_slot1_y = bl_tlc_y + 33

battlelist_region = Region(bl_tlc_x,bl_tlc_y,40,200)

#LIFE AND MANA INFORMATION

try: life_mana_bars = find(Pattern("life_mana_bars.png").exact())
except: raise Exception("Life bars not found!")

#EQUIP INFORMATIONS

try: equip_coords = find("store_inbox.png")
except: raise Exception("Equipment not found!")

equip_coords_x = equip_coords.getTopRight().getX()+5
equip_coords_y = equip_coords.getTopRight().getY()

equip_region = Region((equip_coords_x-115),equip_coords_y,110,163)

#MINIMAP REGION
try: minimap_area = find("minimap_aux.png")
except: raise Exception ("Minimap not found!")

mma_aux_x = minimap_area.getTopLeft().getX()
mma_aux_y = minimap_area.getTopLeft().getY()

minimap_area_x = mma_aux_x - 115
minimap_area_y = mma_aux_y - 49

try:
    sub_zoom = find(Pattern("sub_zoom.png").exact())
    add_zoom = find(Pattern("add_zoom.png").exact())
except: raise Exception ("Zoom buttons not found!")
    
#################################
##     ##    ###    #### ##    ## 
###   ###   ## ##    ##  ###   ## 
#### ####  ##   ##   ##  ####  ## 
## ### ## ##     ##  ##  ## ## ## 
##     ## #########  ##  ##  #### 
##     ## ##     ##  ##  ##   ### 
##     ## ##     ## #### ##    ## 
#################################

#sets running variable to 1
running = 1

#starts healing and attacking threads (if vocation > 0)
start_healing_thread()
if vocation > 0: start_attacking_thread()
print " "

while running == 1:

    encounter = -1
    if label == "hunt": 
        if lure_mode == 1: check_battle_list()
        check_debuffs()
        
    waypointer()

    #gc.collect()

else: 
    popup("END")
    #if console == "simple": closeFrame(0)
