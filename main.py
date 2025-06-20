from flask import Flask, jsonify, request, render_template
from board import ChessBoard
from app.pieces.pawn import Pawn
from app.pieces.knight import Knight
from app.pieces.bishop import Bishop
from app.pieces.rook import Rook
from app.pieces.queen import Queen
from app.pieces.king import King
from app.ia import obtener_mejor_movimiento, evaluar_tablero
app = Flask(__name__, static_url_path="/static", static_folder="static", template_folder="templates")

# Crear el juego
game = ChessBoard()
@app.route('/')
def index():
    return render_template('base.html')  # Tu HTML principal

@app.route('/api/board')
def get_board():
    king_in_check = None
    if game.is_in_check(game.current_turn):
        king_in_check = game.get_king_position(game.current_turn)

    game_over = game.is_game_over()
    winner = None
    if game_over:
        winner = game.get_winner()

    eval_score = evaluar_tablero(game) # <- añade esto

    return jsonify({
        "board": game.get_board_state(),
        "turn": game.current_turn,
        "king_in_check": king_in_check,
        "game_over": game_over,
        "winner": winner,
        "eval": eval_score 
    })

@app.route("/legal_moves", methods=["POST"])
def legal_moves():
        data = request.get_json()
        row, col = data["row"], data["col"]
        piece = game.board[row][col]
        if piece is None:
            return jsonify({"moves": []})
        # Usar game.get_legal_moves para incluir casos especiales como el enroque
        moves = game.get_legal_moves((row, col), game.board, game.last_move)
        return jsonify({"moves": moves})

@app.route("/api/move", methods=["POST"])
def move_piece():
    data = request.get_json()
    from_pos = tuple(data["from"])
    to_pos = tuple(data["to"])
    promotion_choice = data.get("promotion_choice")

    # Verificar si el movimiento cubre el jaque antes de realizarlo
    move_covers_check = game.does_move_cover_check(from_pos, to_pos)
    
    # Realizar el movimiento
    result = game.move_piece(from_pos, to_pos, promotion_choice)
    result["last_move"] = {"from": from_pos, "to": to_pos}
    # Verificar si el movimiento fue un enroque
    result["castle"] = False
    piece = game.board[to_pos[0]][to_pos[1]]
    if isinstance(piece, King) and abs(to_pos[1] - from_pos[1]) == 2:
        result["castle"] = True

    # Verificar si el rey quedó en jaque después del movimiento
    in_check = game.is_in_check(game.current_turn)
    king_pos = game.get_king_position(game.current_turn)

    # Agregar información adicional al resultado
    result["in_check"] = in_check
    result["king_position"] = king_pos
    result["move_does_not_cover_check"] = not move_covers_check

    # Verificar si se requiere promoción
    if isinstance(piece, Pawn) and (to_pos[0] == 0 or to_pos[0] == 7):
        result["promotion_required"] = True
        result["promotion_piece_color"] = piece.color
    else:
        result["promotion_required"] = False

    # Estado del tablero
    result["board"] = game.get_board_state()
    result["stalemate"] = game.stalemate # Verificar si es un ahogado
    # Verificar si el juego ha terminado
    if game.is_game_over():
        result["game_over"] = True
        result["winner"] = game.get_winner()
        result["winner_color"] = game.get_winner()
        result["loser_king_position"] = game.get_king_position(game.get_loser())  # Posición del rey perdedor
        result["king_position"] = game.get_king_position(game.get_winner())  # Posición del rey ganador
        if game.stalemate:
            result["stalemate"] = True
            result["black_king_position"] = game.get_king_position("black")
            result["white_king_position"] = game.get_king_position("white")
    else:
        result["game_over"] = False
    
    return jsonify(result)
@app.route("/promote", methods=["POST"])
def promote():
    data = request.get_json()
    from_pos = tuple(data["from"])
    to_pos = tuple(data["to"])
    piece_type = data["piece_type"].lower()  # Convertir a minúsculas para evitar problemas de coincidencia

    # Verificar que la pieza en la posición 'to' sea un peón
    piece = game.board[to_pos[0]][to_pos[1]]
    if not isinstance(piece, Pawn):
        return jsonify({"success": False, "error": "Solo se puede promocionar un peón"}), 400

    # Promocionar el peón a la pieza seleccionada
    promoted_piece = {
        "queen": Queen,
        "rook": Rook,
        "bishop": Bishop,
        "knight": Knight
    }.get(piece_type)

    if promoted_piece:
        game.board[to_pos[0]][to_pos[1]] = promoted_piece(piece.color)
    else:
        return jsonify({"success": False, "error": "Tipo de pieza no válido"}), 400

    # Cambiar el turno
    game.current_turn = "black" if game.current_turn == "white" else "white"

    return jsonify({
        "success": True,
        "board": game.get_board_state(),
        "turn": game.current_turn
    })
@app.route("/api/reset", methods=["POST"])
def reset_game():
    global game
    game = ChessBoard()
    return jsonify({"success": True, "board": game.get_board_state(), "turn": game.current_turn})

@app.route('/api/ia_move', methods=['POST'])
def ia_move():
    data = request.get_json() or {}
    color = data.get("color", game.current_turn)
    profundidad = data.get("profundidad", 2)
    promotion_choice = data.get("promotion_choice", "queen")
    move = obtener_mejor_movimiento(game, profundidad, color)
    if move is None:
        return jsonify({"success": False, "message": "No hay movimientos posibles"})
    from_pos, to_pos = move
    result = game.move_piece(from_pos, to_pos, promotion_choice=promotion_choice)
    result["from"] = from_pos
    result["to"] = to_pos
    result["board"] = game.get_board_state()
    result["turn"] = game.current_turn
    result["game_over"] = game.is_game_over()
    result["winner"] = game.get_winner()
    result["eval"] = evaluar_tablero(game)
    result["success"] = True

    if result["game_over"]:
        result["winner_color"] = game.get_winner()
        result["loser_king_position"] = game.get_king_position(game.get_loser())
        result["king_position"] = game.get_king_position(game.get_winner())
        if game.stalemate:
            result["stalemate"] = True
            result["black_king_position"] = game.get_king_position("black")
            result["white_king_position"] = game.get_king_position("white")

    return jsonify(result)
if __name__ == "__main__":
    app.run(debug=True)
