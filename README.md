# Multiplayer Pacman Game

A real-time multiplayer chase game where players can join as either a Runner (Pacman) or Chaser. Built with Python Flask, SocketIO, and vanilla JavaScript.

## 🎮 Game Features

- **Multiplayer**: Two-player game with unique room codes
- **Roles**: 
  - Runner: Collect dots while avoiding the chaser
  - Chaser: Chase and catch the runner
- **Power-ups**:
  - 💚 Health Boost: Restores 1 health point
  - ⚡ Speed Boost: Temporary speed increase
  - 🛡️ Shield: Temporary immunity
- **Obstacles**: Deadly obstacles that damage the runner
- **Health System**: Runner has 3 lives, loses health on collision

## 🚀 Play Now

Visit (https://webchaseman-production.up.railway.app/) to play!

## 🎯 How to Play

1. **Create or Join a Room**:
   - Host: Click "Create Room" and share the room code
   - Player 2: Enter room code to join

2. **Choose Your Role**:
   - Runner: Collect dots, avoid obstacles and chaser
   - Chaser: Catch the runner

3. **Controls**:
   - Use arrow keys to move
   - Collect power-ups (Runner only)

4. **Win Conditions**:
   - Runner wins: Collect all dots
   - Chaser wins: Deplete runner's health

## 🛠️ Local Development

1. Clone the repository:
```bash
git clone https://github.com/your-username/your-repo-name.git
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
python server.py
```

4. Visit `http://localhost:5002` in your browser

## 🔧 Tech Stack

- Backend: Python Flask, Flask-SocketIO
- Frontend: HTML, CSS, JavaScript
- Deployment: Railway

## 📝 License

[Your chosen license]

## 🤝 Contributing

Feel free to open issues and pull requests!
