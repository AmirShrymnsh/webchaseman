# Multiplayer Pacman Chase (Web Version)

A web-based multiplayer game where one player chases the other while collecting dots.

## Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
python server.py
```

4. Open your web browser and navigate to:
```
http://localhost:5000
```

## How to Play

1. Open the game in two different browser windows or tabs
2. Each player will be prompted to choose their role:
   - Runner: Collect dots while avoiding the chaser
   - Chaser: Try to catch the runner
3. Controls:
   - Player 1 (WASD): Move using W, A, S, D keys
   - Player 2 (Arrow Keys): Move using arrow keys

## Features

- Real-time multiplayer gameplay
- Role selection (Runner/Chaser)
- Dot collection mechanics
- Grid-based movement
- Visual feedback for player positions and roles

## Technical Details

- Built with Flask and Socket.IO for real-time communication
- Uses HTML5 Canvas for rendering
- Responsive design that works on different screen sizes 