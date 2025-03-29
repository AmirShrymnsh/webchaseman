from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# Game rooms state
rooms = {}

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def create_game_state():
    return {
        'players': {},
        'dots': [],
        'grid_size': {'width': 20, 'height': 20},
        'game_started': False,
        'player_count': 0,
        'ready_players': set()  # This needs to be converted to list for JSON serialization
    }

def generate_dots(game_state):
    dots = []
    for _ in range(20):
        while True:
            x = random.randint(0, game_state['grid_size']['width'] - 1)
            y = random.randint(0, game_state['grid_size']['height'] - 1)
            if not any(d['x'] == x and d['y'] == y for d in dots) and \
               not any(p['x'] == x and p['y'] == y for p in game_state['players'].values()):
                dots.append({'x': x, 'y': y})
                break
    return dots

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('create_room')
def handle_create_room():
    try:
        room_code = generate_room_code()
        while room_code in rooms:  # Ensure unique room code
            room_code = generate_room_code()
        
        # Create new game state
        game_state = create_game_state()
        rooms[room_code] = game_state
        
        # Add player to room
        join_room(room_code)
        game_state['players'][request.sid] = {
            'x': random.randint(0, game_state['grid_size']['width'] - 1),
            'y': random.randint(0, game_state['grid_size']['height'] - 1),
            'role': None,
            'is_host': True
        }
        game_state['player_count'] = 1
        game_state['ready_players'] = []  # Convert set to list for JSON serialization
        
        print(f"Room created: {room_code}")
        print(f"Game state: {game_state}")
        
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
    if request.sid in rooms[data['room_code']]['players']:
        rooms[data['room_code']]['players'][request.sid]['role'] = data['role']
        print(f'Player {request.sid} chose role: {data["role"]}')
        
        # Check if all players have chosen roles
        all_roles_chosen = all(player['role'] is not None for player in rooms[data['room_code']]['players'].values())
        if all_roles_chosen and len(rooms[data['room_code']]['players']) == 2:
            rooms[data['room_code']]['game_started'] = True
            rooms[data['room_code']]['dots'] = generate_dots(rooms[data['room_code']])
            print('Game started!')
        
        emit('game_state', rooms[data['room_code']], room=data['room_code'])

@socketio.on('update_position')
def handle_position_update(data):
    if request.sid in rooms[data['room_code']]['players']:
        player = rooms[data['room_code']]['players'][request.sid]
        new_x = max(0, min(rooms[data['room_code']]['grid_size']['width'] - 1, data['x']))
        new_y = max(0, min(rooms[data['room_code']]['grid_size']['height'] - 1, data['y']))
        
        player['x'] = new_x
        player['y'] = new_y
        
        # Check for dot collection
        for dot in rooms[data['room_code']]['dots'][:]:
            if dot['x'] == new_x and dot['y'] == new_y:
                rooms[data['room_code']]['dots'].remove(dot)
        
        emit('game_state', rooms[data['room_code']], room=data['room_code'])

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
        rooms[room_code]['players'][request.sid] = {
            'x': random.randint(0, rooms[room_code]['grid_size']['width'] - 1),
            'y': random.randint(0, rooms[room_code]['grid_size']['height'] - 1),
            'role': None,
            'is_host': False
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
            if isinstance(game_state['ready_players'], set):
                game_state['ready_players'] = list(game_state['ready_players'])
            game_state['ready_players'].append(request.sid)
            
            # Check if all players are ready and have roles
            all_ready = len(game_state['ready_players']) == 2
            all_roles_chosen = all(player['role'] is not None for player in game_state['players'].values())
            
            if all_ready and all_roles_chosen:
                game_state['game_started'] = True
                game_state['dots'] = generate_dots(game_state)
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
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)