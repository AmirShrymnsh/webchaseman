import os
from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import string

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'secret!')
socketio = SocketIO(app, cors_allowed_origins="*")

# Game rooms state
rooms = {}

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def create_game_state():
    return {
        'players': {},
        'dots': [],
        'obstacles': [],  # Deadly obstacles
        'powerups': [],   # Health, speed boosts, etc
        'grid_size': {'width': 20, 'height': 20},
        'game_started': False,
        'player_count': 0,
        'ready_players': []
    }

def generate_game_elements(game_state):
    # Generate dots
    dots = []
    for _ in range(20):
        x = random.randint(0, game_state['grid_size']['width'] - 1)
        y = random.randint(0, game_state['grid_size']['height'] - 1)
        dots.append({
            'x': x,
            'y': y,
            'type': 'normal',  # normal dots for points
            'value': 1
        })
    
    # Generate obstacles
    obstacles = []
    for _ in range(5):  # 5 deadly obstacles
        x = random.randint(0, game_state['grid_size']['width'] - 1)
        y = random.randint(0, game_state['grid_size']['height'] - 1)
        obstacles.append({
            'x': x,
            'y': y,
            'type': 'deadly'
        })
    
    # Generate powerups
    powerups = []
    powerup_types = ['health', 'speed', 'shield']
    for _ in range(3):  # 3 powerups
        x = random.randint(0, game_state['grid_size']['width'] - 1)
        y = random.randint(0, game_state['grid_size']['height'] - 1)
        powerups.append({
            'x': x,
            'y': y,
            'type': random.choice(powerup_types),
            'duration': 10  # seconds for temporary powerups
        })
    
    return dots, obstacles, powerups

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('create_room')
def handle_create_room():
    try:
        room_code = generate_room_code()
        while room_code in rooms:
            room_code = generate_room_code()
        
        game_state = create_game_state()
        dots, obstacles, powerups = generate_game_elements(game_state)
        game_state['dots'] = dots
        game_state['obstacles'] = obstacles
        game_state['powerups'] = powerups
        
        rooms[room_code] = game_state
        join_room(room_code)
        
        # Initialize player with health and speed
        game_state['players'][request.sid] = {
            'x': random.randint(0, game_state['grid_size']['width'] - 1),
            'y': random.randint(0, game_state['grid_size']['height'] - 1),
            'role': None,
            'is_host': True,
            'health': 3,
            'speed': 1,
            'powerups': []
        }
        
        game_state['player_count'] = 1
        emit('room_created', {
            'room_code': room_code,
            'game_state': game_state,
            'player_id': request.sid
        })
    except Exception as e:
        print(f"Error creating room: {str(e)}")
        emit('room_error', {'message': f'Failed to create room: {str(e)}'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')
    for room_code, game_state in rooms.items():
        if request.sid in game_state['players']:
            del game_state['players'][request.sid]
            game_state['game_started'] = False
            game_state['dots'] = []
            emit('game_state', game_state, room=room_code)

@socketio.on('choose_role')
def handle_role_choice(data):
    try:
        room_code = data['room_code']
        if request.sid in rooms[room_code]['players']:
            player = rooms[room_code]['players'][request.sid]
            player['role'] = data['role']
            # Set health based on role
            if data['role'] == 'runner':
                player['health'] = 3  # Runner starts with 3 health
            else:
                player['health'] = 1  # Chaser only needs 1 health
            
            print(f'Player {request.sid} chose role: {data["role"]} with health: {player["health"]}')
            
            # Check if all players have chosen roles
            all_roles_chosen = all(p['role'] is not None for p in rooms[room_code]['players'].values())
            if all_roles_chosen and len(rooms[room_code]['players']) == 2:
                rooms[room_code]['game_started'] = True
                dots, obstacles, powerups = generate_game_elements(rooms[room_code])
                rooms[room_code]['dots'] = dots
                rooms[room_code]['obstacles'] = obstacles
                rooms[room_code]['powerups'] = powerups
                print('Game started!')
            
            emit('game_state', rooms[room_code], room=room_code)
    except Exception as e:
        print(f"Error in role choice: {str(e)}")

@socketio.on('update_position')
def handle_position_update(data):
    try:
        room_code = data['room_code']
        if room_code in rooms and request.sid in rooms[room_code]['players']:
            game_state = rooms[room_code]
            current_player = game_state['players'][request.sid]
            new_x = max(0, min(game_state['grid_size']['width'] - 1, data['x']))
            new_y = max(0, min(game_state['grid_size']['height'] - 1, data['y']))
            
            # Update position
            current_player['x'] = new_x
            current_player['y'] = new_y
            
            # Check for runner-chaser collision
            for player_id, other_player in game_state['players'].items():
                if player_id != request.sid:  # Different players
                    if other_player['x'] == new_x and other_player['y'] == new_y:
                        runner = None
                        if current_player['role'] == 'runner':
                            runner = current_player
                        elif other_player['role'] == 'runner':
                            runner = other_player
                            
                        if runner and not runner.get('shield', False):
                            print(f"Runner caught! Current health: {runner['health']}")
                            runner['health'] -= 1
                            print(f"New health: {runner['health']}")
                            if runner['health'] <= 0:
                                emit('game_over', {'winner': 'chaser'}, room=room_code)
                                return
                            emit('health_update', {'player_id': runner['id'], 'health': runner['health']}, room=room_code)

            if current_player['role'] == 'runner':
                # Check for dot collection
                for dot in game_state['dots'][:]:
                    if dot['x'] == new_x and dot['y'] == new_y:
                        game_state['dots'].remove(dot)
                        if len(game_state['dots']) == 0:
                            emit('game_over', {'winner': 'runner'}, room=room_code)
                            return

                # Check for powerup collection
                for powerup in game_state['powerups'][:]:
                    if powerup['x'] == new_x and powerup['y'] == new_y:
                        print(f"Powerup collected: {powerup['type']}")  # Debug print
                        if powerup['type'] == 'health':
                            current_player['health'] = min(current_player['health'] + 1, 3)
                        elif powerup['type'] == 'speed':
                            current_player['speed'] = 2
                        elif powerup['type'] == 'shield':
                            current_player['shield'] = True
                        game_state['powerups'].remove(powerup)
                        emit('powerup_collected', {'type': powerup['type']}, room=room_code)

                # Check for obstacle collision
                for obstacle in game_state['obstacles']:
                    if obstacle['x'] == new_x and obstacle['y'] == new_y:
                        if not current_player.get('shield', False):
                            print(f"Hit obstacle! Health: {current_player['health']}")  # Debug print
                            current_player['health'] -= 1
                            if current_player['health'] <= 0:
                                emit('game_over', {'winner': 'chaser'}, room=room_code)
                                return
                            emit('health_update', {'health': current_player['health']}, room=room_code)

            # Debug print
            print(f"Current game state - Players:")
            for pid, p in game_state['players'].items():
                print(f"Player {pid}: Role={p['role']}, Health={p['health']}, Pos=({p['x']},{p['y']})")
            
            emit('game_state', game_state, room=room_code)
            
    except Exception as e:
        print(f"Error updating position: {str(e)}")

@socketio.on('join_room')
def handle_join_room(data):
    try:
        room_code = data['room_code'].upper()
        print(f"Attempting to join room: {room_code}")
        
        if room_code not in rooms:
            emit('room_error', {'message': 'Room not found'})
            return
        
        if rooms[room_code]['player_count'] >= 2:
            emit('room_error', {'message': 'Room is full'})
            return
        
        join_room(room_code)
        # Initialize player with default values
        rooms[room_code]['players'][request.sid] = {
            'x': random.randint(0, rooms[room_code]['grid_size']['width'] - 1),
            'y': random.randint(0, rooms[room_code]['grid_size']['height'] - 1),
            'role': None,
            'is_host': False,
            'health': 3,  # Set initial health for all players
            'speed': 1,
            'shield': False
        }
        rooms[room_code]['player_count'] += 1
        
        emit('room_joined', {
            'game_state': rooms[room_code],
            'player_id': request.sid
        })
        emit('game_state', rooms[room_code], room=room_code)
    except Exception as e:
        print(f"Error joining room: {str(e)}")
        emit('room_error', {'message': f'Failed to join room: {str(e)}'})

@socketio.on('ready_to_start')
def handle_ready_to_start(data):
    try:
        room_code = data['room_code']
        if room_code in rooms:
            game_state = rooms[room_code]
            if request.sid not in game_state['ready_players']:
                game_state['ready_players'].append(request.sid)
            
            # Check if all players are ready and have roles
            all_ready = len(game_state['ready_players']) == 2
            all_roles_chosen = all(player['role'] is not None for player in game_state['players'].values())
            
            if all_ready and all_roles_chosen:
                game_state['game_started'] = True
                # Generate new game elements when game starts
                dots, obstacles, powerups = generate_game_elements(game_state)
                game_state['dots'] = dots
                game_state['obstacles'] = obstacles
                game_state['powerups'] = powerups
                emit('game_started', game_state, room=room_code)
            else:
                emit('waiting_for_players', {
                    'ready_count': len(game_state['ready_players']),
                    'total_needed': 2
                }, room=room_code)
    except Exception as e:
        print(f"Error in ready_to_start: {str(e)}")
        emit('room_error', {'message': f'Error starting game: {str(e)}'})

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5002)