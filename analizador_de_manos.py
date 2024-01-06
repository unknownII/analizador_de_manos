import os
import time
import re
import json

def reload_filelist():
    list_of_files = os.listdir(os.getcwd())
    filelist = {}
    filelist['tournaments'] = []
    filelist['zoomgames'] = []
    filelist['all'] = []
    for filename in list_of_files:
        with open(filename, 'r') as open_file:
            input_file = open_file.read()
            if 'Tournament' in input_file and filename[0:2] == 'HH':
                filelist['tournaments'].append(filename)
            elif 'Zoom Hand' in input_file and filename[0:2] == 'HH':
                filelist['zoomgames'].append(filename)
            if filename[0:2] == 'HH':
                filelist['all'].append(filename)
    return filelist

def build_db(filelist, gametype):
    # Cargar estrategias desde un archivo JSON
    with open("estrategias_preflop.json", "r") as file:
        estrategia_preflop = json.load(file)      
    nr_of_hands = 0
    db = {}
    for filename in filelist[gametype]:
        print(f"Processing file: {filename}")
        #import pdb; pdb.set_trace()  # Establece un punto de ruptura
        hands = hands_in_file(filename)
        for hand in hands:
            print(f'mano num: {hand}')
            nr_of_hands += 1
            count_players(db, hands[hand])
            players = who_is_playing(hands[hand])
            print(f'players: {players}')
            count_all_hands(players, db)
            preflop, flop, turn, river, show, summary = extract_streets(hands[hand])
            numero_mano, numero_torneo, sb, bb = extract_header(hands[hand])
            pos, stack_bb, accion = extract_apalbresoli_pos(hands[hand], bb, preflop)
            hole_cards = extract_hole_cards(hands[hand])  
            hole_cards_normalized = normalize_cards(hole_cards)
            print(f'hole cards: {hole_cards_normalized}')
            print(f'pos={pos}, stack={stack_bb}')
            if stack_bb > 15:
                estrategia_stack = '15+'
            if stack_bb > 9:
                estrategia_stack = '9-15'
            else:
                estrategia_stack = '0-9'
            if pos == 'BTN':
                print(f"Estrategia para {hole_cards_normalized} en {pos}: {estrategia_preflop[pos][estrategia_stack][hole_cards_normalized]}")
                print (f"apalbresoli --> {accion}")
                import pdb; pdb.set_trace()  # Establece un punto de ruptura
            calculate_VPIP_hands(preflop, db)
            calculate_PFR_hands(preflop, db)
            calculate_AFq_hands(flop, turn, river, db)
            calculate_WTSD_hands(show, db)
            calculate_WTFLOP_hands(flop, db)
            calculate_CBET_hands(preflop, flop, db)
            won_showdown(show, db)
    return db, nr_of_hands

def hands_in_file(filename):
    with open(filename, 'r') as open_file:
        input_file = open_file.read()
        hands = {}
        eof = 0
        #import pdb; pdb.set_trace()  # Establece un punto de ruptura
        while eof != 1:
            hand_begins = input_file.find('Hand #')
            hand_number_begins = hand_begins + 6
            hand_number_ends = input_file.find(': ', hand_number_begins)
            hand_ends = input_file.find('Hand #', hand_number_ends)

            if len(input_file[hand_number_begins:hand_number_ends]) == 12:
                hands[input_file[hand_number_begins:hand_number_ends]] = input_file[hand_begins-11:hand_ends - 18]
            input_file = input_file[hand_ends - 15:]
            if hand_begins == -1:
                eof = 1
    return hands

def count_players(db, hand):
    lines_of_hand = hand.splitlines()
    if len(lines_of_hand) > 2:
        for i in range(2, 12):
            current_line = lines_of_hand[i]
            if current_line[0:5] == 'Seat ':
                name_begins = current_line.find(': ') + 2
                name_ends = current_line[name_begins+2:].find(' (')
                name = current_line[name_begins:name_begins+name_ends+2]
                if name not in db:
                    db[name] = {'hands_played': 0,
                                'VPIP_hands': 0,
                                'VPIP': 0,
                                'PFR_hands': 0,
                                'PFR': 0,
                                'POST_FLOP_AGG': 0,
                                'POST_FLOP_PASSIVE': 0,
                                'AFq': 0,
                                'WTSD_HANDS': 0,
                                'WTSD_PERCENTAGE': 0,
                                'WTFLOP_HANDS': 0,
                                'CBET_HANDS': 0,
                                'last_to_raise_preflop': 0,
                                'CBET': 0,
                                'won_showdown': 0,
                                'won_showdown_percentage': 0,
                                }

def who_is_playing(hand):
    players = []
    lines_of_hand = hand.splitlines()
    if len(lines_of_hand) > 2:
        for i in range(1, 11):
            current_line = lines_of_hand[1+i]
            if current_line[0:5] == 'Seat ':
                name_begins = current_line.find(': ') + 2
                name_ends = current_line[name_begins+2:].find(' (')
                name = current_line[name_begins:name_ends+name_begins+2]
                players.append(name)
    return players

def count_all_hands(players, db):
    for player in players:
        db[player]['hands_played'] += 1

def extract_streets(hand):
    preflop = extract_preflop(hand)
    flop = extract_flop(hand)
    turn = extract_turn(hand)
    river = extract_river(hand)
    show = extract_show(hand)
    summary = extract_summary(hand)
    print(f'preflop:\n{preflop}')
    #print(f'flop:\n{flop}')
    #print(f'river:\n{river}')
    #print(f'show:\n{show}')
    #print(f'summary:\n{summary}')
    return preflop, flop, turn, river, show, summary

def normalize_cards(pair_cards):
    carta1 = pair_cards[0:1]
    carta2 = pair_cards[3:4]
    palo1 = pair_cards[1:2]
    palo2 = pair_cards[4:5]
    if carta1 == carta2:
        return carta1+carta2

    if palo1 == palo2:
        cartas = [carta1, carta2]
        valores = "23456789TJQKA"
        cartas_ordenadas = sorted(cartas, key=lambda x: valores.index(x[0]), reverse=True)
        return f"{cartas_ordenadas[0]+cartas_ordenadas[1]}s"

    else:
        cartas = [carta1, carta2]
        valores = "23456789TJQKA"
        cartas_ordenadas = sorted(cartas, key=lambda x: valores.index(x[0]), reverse=True)
        return f"{cartas_ordenadas[0]+cartas_ordenadas[1]}o"


def extract_hole_cards(hand):
    cards_pos = hand.find('Dealt to apalbresoli ') + 21
    cards = hand[cards_pos+1:cards_pos + 6]
    return cards

def extract_apalbresoli_pos(hand, BB, preflop):
    #import pdb; pdb.set_trace()  # Establece un punto de ruptura
    pos = None
    if (hand.find('apalbresoli: posts big blind')) != -1:
        if len(who_is_playing(hand)) == 3:
            #apalbresoli is BB
            #BTN limp + SB limp = BBvsBTN LIMP
            patron = r'(\w+): calls (\d+)'
            lines_of_preflop = preflop.splitlines(True)        
            if re.match(patron, lines_of_preflop[0]):
                accion = 'calls'
                pos = 'BBvsBTN LIMP'

            patron = r'(\w+): raises (\d+) to (\d+)'
            if re.match(patron, lines_of_preflop[0]):
                accion = 'raises'
                raise_bb = int(re.match(patron, lines_of_preflop[0]).group(2))/int(BB)
                if raise_bb <= 3:
                    pos = 'BBvsBTN MR'
                else:
                    pos = 'BBvsBTN OS'

            if re.match(patron, lines_of_preflop[1]):
                accion = 'raises'
                raise_bb = int(re.match(patron, lines_of_preflop[1]).group(2))/int(BB)
                if raise_bb <= 3:
                    pos = 'BBvsSB MR'
                else:
                    pos = 'BBvsSB OS'


        if len(who_is_playing(hand)) == 2:
            #Sólo quedan 2 judadores HU
            patron = r'(\w+): calls (\d+)'
            lines_of_preflop = preflop.splitlines(True)        
            if re.match(patron, lines_of_preflop[0]):
                accion = 'calls'
                pos = 'BBvsSB LIMP'
            patron = r'(\w+): raises (\d+) to (\d+)'
            if re.match(patron, lines_of_preflop[0]):
                accion = 'raises'
                raise_bb = int(re.match(patron, lines_of_preflop[0]).group(2))/int(BB)
                if raise_bb <= 3:
                    pos = 'BBvsSB MR'
                else:
                    pos = 'BBvsSB OS'


    elif (hand.find('apalbresoli: posts small blind')) != -1:
	    #apalbresoli is SB
        if len(who_is_playing(hand)) == 3:
            patron = r'(\w+): calls (\d+)'
            lines_of_preflop = preflop.splitlines(True)        
            if re.match(patron, lines_of_preflop[0]):
                accion = 'calls'
                pos = 'SBvsBTN LIMP'
            patron = r'(\w+): raises (\d+) to (\d+)'
            if re.match(patron, lines_of_preflop[0]):
                accion = 'raises'
                raise_bb = int(re.match(patron, lines_of_preflop[0]).group(2))/int(BB)
                if raise_bb <= 3:
                    pos = 'SBvsBTN MR'
                else:
                    pos = 'SBvsBTN OS'
            if (len(lines_of_preflop) > 3):
                #casi seguro hay raise de BB
                patron = r'(\w+): raises (\d+) to (\d+)'
                if re.match(patron, lines_of_preflop[2]):
                    pos = 'SB 3H'
        if len(who_is_playing(hand)) == 2:
            pos = 'SB UP'


    else:
	#apalbresoli is BTN
        pos = 'BTN'
        accion = extract_action_apalbresoli(preflop)


    stack = extract_player_stack(hand, 'apalbresoli')
    stack_bb = int(stack) / int(BB)    
    if pos is not None:
        print(f'apalbresoli is {pos} con {stack_bb}')    
    return pos, stack_bb, accion

def extract_action_apalbresoli(preflop):
    list_action= []
    lines = preflop.splitlines()
    for line in lines:
        action_pos = line.find('apalbresoli: ')
        if action_pos != -1:
                action_end = line[15:].find(' ')
                action = line[13:15+action_end]
                list_action.append(action)
    return list_action
                

def extract_player_stack(hand, player):

    # Definir el patrón de expresión regular
    patron = r"Table '(\d+) (\d+)' (\d+)-max Seat #(\d+) is the button"
    lines_of_hand = hand.splitlines(True)
    linea =  lines_of_hand[1]
    coincidencia = re.match(patron, linea)

    # Verificar si hubo una coincidencia
    if coincidencia:
        # El grupo 3 es el número de asientos
        if coincidencia.group(3) == '3':
            # Definir el patrón de expresión regular
            patron = r'Seat (\d+): (\w+) \((\d+) in chips\)'
            lines_of_hand = hand.splitlines(True)

            coincidencia_seat1 = re.match(patron, lines_of_hand[2])
            coincidencia_seat2 = re.match(patron, lines_of_hand[3])
            coincidencia_seat3 = re.match(patron, lines_of_hand[4])
            if coincidencia_seat1 :
                fichas_en_chips = coincidencia_seat1.group(3)
            elif coincidencia_seat2 :
                fichas_en_chips = coincidencia_seat2.group(3)
            elif coincidencia_seat3 :
                fichas_en_chips = coincidencia_seat3.group(3)
            return fichas_en_chips
    else:
        # En caso de no haber coincidencia, devolver None o manejar el error según sea necesario
        return None

def extract_player_pos(hand, BB, player):
    # Definir el patrón de expresión regular
    patron = r'Seat (\d+): (\w+) \((\d+) in chips\)'
    lines_of_hand = hand.splitlines(True)
    linea =  lines_of_hand[2]

    # Intentar hacer coincidir el patrón en la línea
    coincidencia = re.match(patron, linea)

    # Verificar si hubo una coincidencia
    if coincidencia:
        # Extraer información utilizando grupos de captura
        numero_asiento = coincidencia.group(1)
        nombre_jugador = coincidencia.group(2)
        fichas_en_chips = coincidencia.group(3)
        fichas_en_ciegas = fichas_en_chips / BB
        print(f'El jugador {nombre_jugador} tiene {fichas_en_ciegas}')

        # Devolver los valores extraídos
        return numero_asiento, nombre_jugador, fichas_en_ciegas 
    else:
        # En caso de no haber coincidencia, devolver None o manejar el error según sea necesario
        return None

def extract_header(hand):
    # Definir el patrón de expresiones regulares
    patron = r"PokerStars Hand #(\d+): Tournament #(\d+), \$([\d.]+)\+\$([\d.]+) USD Hold'em No Limit - Level ([IVXLCDM]+) \((\d+)/(\d+)\) - (.+)$"
    lines_of_hand = hand.splitlines(True)
    linea =  lines_of_hand[0]
    # Aplicar el patrón a la línea
    coincidencia = re.match(patron, linea)

    if coincidencia:
        numero_mano = coincidencia.group(1)
        numero_torneo = coincidencia.group(2)
        sb_dolar = coincidencia.group(3)
        bb_dolar = coincidencia.group(4)
        nivel_romano = coincidencia.group(5)
        sb = coincidencia.group(6)
        bb = coincidencia.group(7)

        # Puedes imprimir o retornar la información según tus necesidades
        print("Número de mano:", numero_mano)
        print("Número de torneo:", numero_torneo)
        print("SB:", sb)
        print("BB:", bb)
        print("Tamaño SB en dólares:", sb_dolar)
        print("Tamaño BB en dólares:", bb_dolar)
        print("Nivel (romano):", nivel_romano)
        return numero_mano, numero_torneo, sb, bb


def extract_preflop(hand):
    preflop_pos = hand.find('*** HOLE CARDS ***') + 18
    preflop_end = hand.find('*** FLOP ***')
    if preflop_end == -1:
        preflop_end = hand.find('*** SUMMARY ***')
    hand = hand[preflop_pos:preflop_end]
    lines_of_hand = hand.splitlines(True)
    preflop_list = lines_of_hand[2:]
    preflop = ''.join(preflop_list)
    return preflop

def extract_flop(hand):
    flop_pos = hand.find('*** FLOP ***') + 12
    if flop_pos-12 == -1:
        return 'none'
    flop_end = hand.find('*** TURN ***')
    if flop_end == -1:
        flop_end = hand.find('*** SUMMARY ***')
    hand = hand[flop_pos:flop_end]
    lines_of_hand = hand.splitlines(True)
    flop_list = lines_of_hand[1:]
    flop = ''.join(flop_list)
    return flop

def extract_turn(hand):
    turn_pos = hand.find('*** TURN ***') + 12
    if turn_pos-12 == -1:
        return 'none'
    turn_end = hand.find('*** RIVER ***')
    if turn_end == -1:
        turn_end = hand.find('*** SUMMARY ***')
    hand = hand[turn_pos:turn_end]
    lines_of_hand = hand.splitlines(True)
    turn_list = lines_of_hand[1:]
    turn = ''.join(turn_list)
    return turn

def extract_river(hand):
    river_pos = hand.find('*** RIVER ***') + 13
    if river_pos-13 == -1:
        return 'none'
    river_end = hand.find('*** SHOW DOWN ***')
    if river_end == -1:
        river_end = hand.find('*** SUMMARY ***')
    hand = hand[river_pos:river_end]
    lines_of_hand = hand.splitlines(True)
    river_list = lines_of_hand[1:]
    river = ''.join(river_list)
    return river

def extract_show(hand):
    show_pos = hand.find('*** SHOW DOWN ***') + 17
    if show_pos-17 == -1:
        return 'none'
    show_end = hand.find('*** SUMMARY ***')
    if show_end == -1:
        show_end = hand.find('*** SUMMARY ***')
    hand = hand[show_pos:show_end]
    lines_of_hand = hand.splitlines(True)
    show_list = lines_of_hand[1:]
    show = ''.join(show_list)
    return show

def extract_summary(hand):
    summary_pos = hand.find('*** SUMMARY ***') + 17
    if summary_pos-17 == -1:
        return 'none'
    summary_end = -1
    hand = hand[summary_pos:summary_end]
    lines_of_hand = hand.splitlines(True)
    summary_list = lines_of_hand[1:]
    summary = ''.join(summary_list)
    return summary

###############################################################################
# calculate_VPIP_hands calculates the amount of hands for each player, when   #
# money was voluntarily put into pot(hence the name - VPIP).                  # 
###############################################################################

def calculate_VPIP_hands(preflop, db):
    lines = preflop.splitlines()
    for line in lines:
        action_pos = line.find(': ')
        if action_pos != -1:
            action_end = line[action_pos+2:].find(' ')
            action = line[action_pos+2:action_pos+2+action_end]
# A call or a raise is considered a voluntary action to put money into pot
            if action == 'calls' or action == 'raises':
                name = line[:action_pos]
                if name not in db:
                    parenthesis_start = name.find(' (')
                    name = name[:parenthesis_start]
                db[name]['VPIP_hands']=db[name]['VPIP_hands'] + 1

###############################################################################
# calculate_PFR_hands calculates the amount of hands for each player, when    #
# a player performs a pre flop raise(hence the name - PFR).                   #
###############################################################################

def calculate_PFR_hands(preflop, db):
    lines = preflop.splitlines()
    for line in lines:
        action_pos = line.find(': ')
        if action_pos != -1:
            action_end = line[action_pos+2:].find(' ')
            action = line[action_pos+2:action_pos+2+action_end]
            if action == 'raises':
                name = line[:action_pos]
                if name not in db:
                    parenthesis_start = name.find(' (')
                    name = name[:parenthesis_start]
                db[name]['PFR_hands']=db[name]['PFR_hands'] + 1
    
'''
def calculate_AFq_hands(flop, turn, river, db):
    actions_pos = flop.find('apalbresoli')
    actions_end = flop.find('\n', actions_pos)
    actions = flop[actions_pos:actions_end]
    # Verificar si no hay acciones en el flop
    if actions == 'none':
        return  # Salir de la función si no hay acciones en el flop

    #actions += turn
    #actions += river
    #print(f'actions: {actions}')  # Agregar esta línea para imprimir el valor de actions

    last_to_raise = db[actions[0:actions.find(':')]]['last_to_raise_preflop']
    if actions.find(last_to_raise) == -1:
        db[actions[0:actions.find(':')]]['POST_FLOP_PASSIVE'] += 1
    else:
        db[actions[0:actions.find(':')]]['POST_FLOP_AGG'] += 1
    db[actions[0:actions.find(':')]]['AFq'] = db[actions[0:actions.find(':')]]['POST_FLOP_AGG'] / (db[actions[0:actions.find(':')]]['POST_FLOP_PASSIVE'] + db[actions[0:actions.find(':')]]['POST_FLOP_AGG'])
'''

###############################################################################
# calculate_AFq_hands calculates the amount of hands for each player, when    #
# a player showed aggression in the post flop and played passively in the     #
# post flop stage of the current hand(AFq stands for aggression frequency).   #
# Aggression frquency is calculated by dividing the amount of post flop raises#
# and bets by the amount of post flop raises, bets, calls and folds.          #
###############################################################################

def calculate_AFq_hands(flop, turn, river, db):
    phase_of_game = [flop, turn, river]
    for phase in phase_of_game:
        lines = phase.splitlines()
        for line in lines:
            action_pos = line.find(': ')
            if action_pos != -1:
                action_end = line[action_pos+2:].find(' ')
                action = line[action_pos+2:action_pos+2+action_end]
                if action == 'raises' or action == 'bets':
                    name = line[:action_pos]
                    if name not in db:
                        parenthesis_start = name.find(' (')
                        name = name[:parenthesis_start]
                    db[name]['POST_FLOP_AGG']=db[name]['POST_FLOP_AGG'] + 1
                if action == 'raises' or action == 'bets' or action == 'calls' or action == 'folds':
                    name = line[:action_pos]
                    if name not in db:
                        parenthesis_start = name.find(' (')
                        name = name[:parenthesis_start]
                    db[name]['POST_FLOP_PASSIVE']=db[name]['POST_FLOP_PASSIVE'] + 1

###############################################################################
# calculate_WTSD_hands calculates the amount of hands for each player, when   #
# a player went to show down(hence the name - WTSD).                          #
###############################################################################
    
def calculate_WTSD_hands(show,db):
    lines = show.splitlines()
    for line in lines:
        action_pos = line.find(': ')
        if action_pos != -1:
            name = line[:action_pos]
            if name not in db:
                parenthesis_start = name.find(' (')
                name = name[:parenthesis_start]
            db[name]['WTSD_HANDS'] = db[name]['WTSD_HANDS'] + 1

###############################################################################
# calculate_WTFLOP_hands calculates the amount of hands for each player, when #
# a player went to flop.                                                      #
###############################################################################

def calculate_WTFLOP_hands(flop, db):
    lines = flop.splitlines()
    for line in lines:
        action_pos = line.find(': ')
        if action_pos != -1:
            name = line[:action_pos]
            if name not in db:
                parenthesis_start = name.find(' (')
                name = name[:parenthesis_start]
            db[name]['WTFLOP_HANDS'] = db[name]['WTFLOP_HANDS'] + 1

###############################################################################
# calculate_CBET_hands calculates the amount of hands for each player, when   #
# a payer made a continuation bet.                                            #
###############################################################################

def calculate_CBET_hands(preflop, flop, db):
    preflop_raise = last_to_raise_pre_flop(preflop, flop, db)
    post_flop_bet = first_to_bet_post_flop(flop, db)
    if preflop_raise == post_flop_bet:
        db[preflop_raise]['CBET_HANDS'] = db[preflop_raise]['CBET_HANDS'] + 1

###############################################################################
# This procedure finds which player was the last to raise in the preflop phase#
# of the game, it also calculates how many times each player was the last to  #
# raise in the preflop phase of the game.                                     #                                                                #
###############################################################################

def last_to_raise_pre_flop(preflop, flop, db):
    last_to_raise = 'n/a'
    lines = preflop.splitlines()
    for line in lines:
        action_pos = line.find(': ')
        if action_pos != -1:
                action_end = line[action_pos+2:].find(' ')
                action = line[action_pos+2:action_pos+2+action_end]
                if action == 'raises':
                    name = line[:action_pos]
                    if name not in db:
                        parenthesis_start = name.find(' (')
                        name = name[:parenthesis_start]
                    last_to_raise = name
    if last_to_raise != 'n/a' and flop != 'none':
        db[last_to_raise]['last_to_raise_preflop'] = db[last_to_raise]['last_to_raise_preflop'] + 1
    return last_to_raise

###############################################################################
# This procedure finds which player was the first one to bet in the flop phase#
# of the game.                                                                #
###############################################################################

def first_to_bet_post_flop(flop, db):
    lines = flop.splitlines()
    for line in lines:
        action_pos = line.find(': ')
        if action_pos != -1:
                action_end = line[action_pos+2:].find(' ')
                action = line[action_pos+2:action_pos+2+action_end]
                if action == 'bets' or action == 'raises':
                    name = line[:action_pos]
                    if name not in db:
                        parenthesis_start = name.find(' (')
                        name = name[:parenthesis_start]
                    return name
    return 'none1'

###############################################################################
# won_showdown calculates the amount of hands for each player, when a player  #
# won the pot or at least tied(which equals to winning or at least not loosing#
# money).                                                                     #
###############################################################################
                    
def won_showdown(show, db):
    print(f'won_showdown: {show}')
    
    if show != 'none':
        names = []
        lines = show.splitlines()
        for line in lines:
            action_pos = line.find(': ')
            print(f'action_pos: {action_pos}')
            if action_pos == -1:
                action_pos = line.find(' collected')
                if action_pos != -1:
                    action_end = line[action_pos+1:].find(' ')
                    action = line[action_pos+1:action_pos+1+action_end]
                    #print(filename)
                    #print(hand)
                    #print(action)
                    #raw_input()
                    if action == 'collected':
                        name = line[:action_pos]
                        if name not in db:
                            parenthesis_start = name.find(' (')
                            name = name[:parenthesis_start]
                        names.append(name)
        for entry in names:
            db[entry]['won_showdown'] = db[entry]['won_showdown'] + 1

###############################################################################
# This procedure, whie using statistics collected, performs the calculations  #
# required to get the percentages of every statistic(useful ones).            #
###############################################################################

def calculations(db):
    for name in db:
        hands_played = db[name]['hands_played']
        hands_played = hands_played + 0.0 # This converts an integer to a real number
        VPIP_hands = db[name]['VPIP_hands']
        VPIP_hands = VPIP_hands + 0.0
        db[name]['VPIP'] = (VPIP_hands/hands_played)*100
        PFR_hands = db[name]['PFR_hands']
        PFR_hands = PFR_hands + 0.0
        db[name]['PFR'] = (PFR_hands/hands_played)*100
        POST_FLOP_AGG = db[name]['POST_FLOP_AGG']
        POST_FLOP_PASSIVE = db[name]['POST_FLOP_PASSIVE']
        POST_FLOP_AGG = POST_FLOP_AGG + 0.0
        POST_FLOP_PASSIVE = POST_FLOP_PASSIVE + 0.0
        if POST_FLOP_PASSIVE != 0.0:
            db[name]['AFq'] = (POST_FLOP_AGG/POST_FLOP_PASSIVE) * 100
        WTSD_HANDS = db[name]['WTSD_HANDS'] + 0.0
        WTFLOP_HANDS = db[name]['WTFLOP_HANDS'] + 0.0
        if WTFLOP_HANDS != 0.0:
            db[name]['WTSD_PERCENTAGE'] = WTSD_HANDS/WTFLOP_HANDS * 100
        CBET_HANDS = db[name]['CBET_HANDS'] +0.0
        last_to_raise_preflop = db[name]['last_to_raise_preflop'] + 0.0
        if last_to_raise_preflop != 0:
            db[name]['CBET'] = (CBET_HANDS/last_to_raise_preflop) * 100
        won_showdown = db[name]['won_showdown'] + 0.0
        if WTSD_HANDS != 0:
            db[name]['won_showdown_percentage'] = (won_showdown/WTSD_HANDS) * 100
    return db

###############################################################################
# This is a cycle where the user enters names of the players he/she is        #
# interested in and gets the statistics of thet player if the player is in the#
# database.                                                                   #
###############################################################################

def user_cycle(db):
    IO = 1
    while IO != 0:
        print( 'Enter the name of the player or "exit" to exit the current gametype: ', end='')
        name = input()
        if name in db:
           print('Statistics for ' + name + ':')
           print('Hands played with this player: ' + str(db[name]['hands_played']))
           print('Voluntarily puts money into pot: ' + str(db[name]['VPIP']) + '%')
           print('Preflop raise: ' + str(db[name]['PFR']) + '%')
           print('Continuation bets: ' + str(db[name]['CBET']) + '%')
           print('Aggression frequency: ' + str(db[name]['AFq']) + '%')
           print('Went to show down: ' + str(db[name]['WTSD_PERCENTAGE']) + '%')
           print('Won show down: ' + str(db[name]['won_showdown_percentage']) + '%')
           print('')
        elif name == 'exit' or name == '"exit"':
            clear = lambda: os.system('cls')
            clear()
            IO = 0
        else:
            print('The name '+name+' is not found in your database...')
            print('Press ENTER to continue...')
            input()
    return


if __name__ == '__main__':
    start_time = time.time()
    sws = time.process_time()
    filelist = reload_filelist()
    db, nr_of_hands = build_db(filelist, 'all')
    print('Processed', nr_of_hands, 'hands in', round(time.time() - start_time, 2), 'seconds.')
    swe = time.process_time()
    sw = swe - sws

    if sw != 0:
        hands_per_second = int(nr_of_hands / sw)
    else:
        hands_per_second = 0

    print('Database loaded ' + str(nr_of_hands) + ' hands in ' + str(sw) + ' seconds at ' +
        str(hands_per_second) + ' hands per second...')

    db = calculations(db)
    print('Database calculations performed...')
    print('Press ENTER to continue...')
    input()
    print('Initializing interface...')
    time.sleep(1)
    clear = lambda: os.system('cls' if os.name == 'nt' else 'clear')
    clear()
    user_cycle(db)



    # Imprimir estadísticas para cada jugador
    for player, stats in db.items():
        print(f'\nEstadísticas para el jugador {player}:')
        print(f'  - Manos jugadas: {stats["hands_played"]}')
        print(f'  - VPIP: {stats["VPIP"]}')
        print(f'  - VPIP_hands: {stats["VPIP_hands"]}')
        print(f'  - PFR: {stats["PFR"]}')
        print(f'  - AFq: {stats["AFq"]}')
        print(f'  - WTSD: {stats["WTSD_PERCENTAGE"]}')
        #print(f'  - WTFLOP: {stats["WTFLOP_PERCENTAGE"]}')
        #print(f'  - CBET: {stats["CBET_PERCENTAGE"]}')
        print(f'  - Ganó en showdown: {stats["won_showdown_percentage"]}')
  

