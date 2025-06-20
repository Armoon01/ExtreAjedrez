from app.pieces.pawn import Pawn
from app.pieces.knight import Knight
from app.pieces.bishop import Bishop
from app.pieces.rook import Rook
from app.pieces.queen import Queen
from app.pieces.king import King

class ChessBoard:
    def __init__(self):
        self.board = self.create_board()
        self.current_turn = "white"
        self.last_move = None
        self.winner = None
        self.stalemate = False

    def create_board(self):
        board = [[None for _ in range(8)] for _ in range(8)]

        for y in range(8):
            board[6][y] = Pawn("white")
            board[1][y] = Pawn("black")

        board[7][1] = Knight("white")
        board[7][6] = Knight("white")
        board[0][1] = Knight("black")
        board[0][6] = Knight("black")

        board[7][2] = Bishop("white")
        board[7][5] = Bishop("white")
        board[0][2] = Bishop("black")
        board[0][5] = Bishop("black")

        board[7][0] = Rook("white")
        board[7][7] = Rook("white")
        board[0][0] = Rook("black")
        board[0][7] = Rook("black")

        board[7][3] = Queen("white")
        board[0][3] = Queen("black")

        board[7][4] = King("white")
        board[0][4] = King("black")

        return board

    def move_piece(self, from_pos, to_pos, promotion_choice=None):
        x1, y1 = from_pos
        x2, y2 = to_pos

        piece = self.board[x1][y1]
        if not piece:
            return {
                "success": False,
                "message": "No hay ninguna pieza en la posición inicial.",
                "board": self.get_board_state()
            }

        if piece.color != self.current_turn:
            return {
                "success": False,
                "message": f"No es el turno de las piezas {piece.color}.",
                "board": self.get_board_state()
            }

        legal_moves = self.get_legal_moves((x1, y1), self.board, self.last_move)
        if (x2, y2) not in legal_moves:
            return {
                "success": False,
                "message": "Movimiento no permitido.",
                "board": self.get_board_state()
            }

        # Verificar si el movimiento es un enroque
        if isinstance(piece, King) and abs(y2 - y1) == 2:
            if y2 > y1:  # Enroque corto
                self.board[x1][5] = self.board[x1][7]  # Mover la torre
                self.board[x1][7] = None
            else:  # Enroque largo
                self.board[x1][3] = self.board[x1][0]  # Mover la torre
                self.board[x1][0] = None

        # Registrar la pieza capturada antes de realizar el movimiento
        captured_piece = self.board[x2][y2]

        # Realizar el movimiento normal
        self.board[x2][y2] = piece
        self.board[x1][y1] = None

        # Actualizar el estado del rey o la torre si se movieron
        if isinstance(piece, King):
            piece.has_moved = True
        if isinstance(piece, Rook):
            piece.has_moved = True

        # Manejar captura al paso
        if isinstance(piece, Pawn) and self.last_move:
            last_from, last_to, last_piece = self.last_move
            if abs(x1 - x2) == 1 and y1 != y2 and not captured_piece:
                if isinstance(last_piece, Pawn) and abs(last_from[0] - last_to[0]) == 2 and last_to[1] == y2:
                    captured_piece = self.board[last_to[0]][last_to[1]]
                    self.board[last_to[0]][last_to[1]] = None

        # Manejar promoción
        if isinstance(piece, Pawn) and (x2 == 0 or x2 == 7):
            if promotion_choice is None:
                return {
                    "success": True,
                    "promotion_required": True,
                    "board": self.get_board_state(),
                    "turn": self.current_turn,
                    "in_check": self.is_in_check(self.current_turn),
                    "king_position": self.get_king_position(self.current_turn)
                }
            if promotion_choice not in ["queen", "rook", "bishop", "knight"]:
                return {
                    "success": False,
                    "message": "Elección de promoción inválida.",
                    "board": self.get_board_state()
                }
            if promotion_choice == "queen":
                self.board[x2][y2] = Queen(piece.color)
            elif promotion_choice == "rook":
                self.board[x2][y2] = Rook(piece.color)
            elif promotion_choice == "bishop":
                self.board[x2][y2] = Bishop(piece.color)
            elif promotion_choice == "knight":
                self.board[x2][y2] = Knight(piece.color)

        # Actualizar el turno
        self.last_move = (from_pos, to_pos, piece)
        self.current_turn = "black" if self.current_turn == "white" else "white"

        return {
            "success": True,
            "message": "Movimiento realizado con éxito.",
            "board": self.get_board_state(),
            "turn": self.current_turn,
            "in_check": self.is_in_check(self.current_turn),
            "king_position": self.get_king_position(self.current_turn),
            "captured_piece": {
                "type": captured_piece.name.lower(),
                "color": captured_piece.color
            } if captured_piece else None
        }

    def get_legal_moves(self, pos, board, last_move):
        x, y = pos
        piece = board[x][y]

        if not piece:
            return []

        possible_moves = piece.get_legal_moves((x, y), board, last_move)

        # Si la pieza es un rey, verificar el enroque
        if isinstance(piece, King) and not piece.has_moved:
            # Enroque corto (hacia la derecha)
            if self.can_castle_kingside(piece.color):
                possible_moves.append((x, y + 2))
            # Enroque largo (hacia la izquierda)
            if self.can_castle_queenside(piece.color):
                possible_moves.append((x, y - 2))

        legal_moves = []
        for move in possible_moves:
            from_pos = (x, y)
            to_pos = move

            captured_piece = board[to_pos[0]][to_pos[1]]
            board[to_pos[0]][to_pos[1]] = piece
            board[x][y] = None

            if not self.is_in_check(piece.color):
                legal_moves.append(to_pos)

            board[x][y] = piece
            board[to_pos[0]][to_pos[1]] = captured_piece

        return legal_moves

    def can_castle_kingside(self, color):
        row = 7 if color == "white" else 0
        king = self.board[row][4]
        rook = self.board[row][7]

        if not isinstance(king, King) or not isinstance(rook, Rook):
            return False
        if king.has_moved or rook.has_moved:
            return False
        if self.board[row][5] or self.board[row][6]:
            return False
        if self.is_in_check(color):
            return False
        if self.does_move_cover_check((row, 4), (row, 5)) or self.does_move_cover_check((row, 4), (row, 6)):
            return False

        return True

    def can_castle_queenside(self, color):
        row = 7 if color == "white" else 0
        king = self.board[row][4]
        rook = self.board[row][0]

        if not isinstance(king, King) or not isinstance(rook, Rook):
            return False
        if king.has_moved or rook.has_moved:
            return False
        if self.board[row][1] or self.board[row][2] or self.board[row][3]:
            return False
        if self.is_in_check(color):
            return False
        if self.does_move_cover_check((row, 4), (row, 3)) or self.does_move_cover_check((row, 4), (row, 2)):
            return False

        return True

    def get_board_state(self):
        state = []
        for row in self.board:
            state_row = []
            for piece in row:
                if piece:
                    state_row.append({
                        "color": piece.color,
                        "type": piece.name.lower()
                    })
                else:
                    state_row.append(None)
            state.append(state_row)
        return state

    def is_in_check(self, color):
        king_pos = self.get_king_position(color)
        if not king_pos:
            return False

        for x in range(8):
            for y in range(8):
                piece = self.board[x][y]
                if piece and piece.color != color:
                    if king_pos in piece.get_legal_moves((x, y), self.board, self.last_move):
                        return True
        return False

    def is_checkmate(self):
        """Devuelve True si el jugador actual está en jaque mate."""
        if not self.is_in_check(self.current_turn):
            return False
        # Si está en jaque y no tiene movimientos legales, es mate
        for x in range(8):
            for y in range(8):
                piece = self.board[x][y]
                if piece and piece.color == self.current_turn:
                    moves = self.get_legal_moves((x, y), self.board, self.last_move)
                    if moves:
                        return False
        return True

    def get_loser(self):
        if self.winner == "white":
            return "black"
        elif self.winner == "black":
            return "white"
        return None

    def get_king_position(self, color):
        for x in range(8):
            for y in range(8):
                piece = self.board[x][y]
                if piece and piece.name.lower() == 'k' and piece.color == color:
                    return (x, y)
        return None

    def setup_stalemate_board(self):
        """Configura el tablero en una situación de ahogado."""
        self.board = [[None for _ in range(8)] for _ in range(8)]
        self.board[7][7] = King("black")  # Rey negro en h1
        self.board[7][7].has_moved = True
        self.board[5][6] = Queen("white")  # Reina blanca en g3
        self.board[5][5] = King("white")  # Rey blanco en f3
        self.board[5][5].has_moved = True
        self.current_turn = "black"
        self.winner = None

    def is_game_over(self):
        """Verifica si el jugador actual tiene algún movimiento legal."""
        # Verificar si el jugador actual tiene movimientos legales
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece and piece.color == self.current_turn:
                    moves = self.get_legal_moves((row, col), self.board, self.last_move)
                    if moves:
                        return False

        # Si no hay movimientos legales, verificar si es jaque mate o ahogado
        if self.is_in_check(self.current_turn):
            self.stalemate = False  # Es jaque mate
            self.winner = "black" if self.current_turn == "white" else "white"
        else:
            self.winner = None  # Empate por ahogado
            self.stalemate = True
        return True

    def get_winner(self):
        return self.winner

    def does_move_cover_check(self, from_pos, to_pos):
        """Verifica si un movimiento cubre el jaque o deja al rey en jaque."""
        moving_piece = self.board[from_pos[0]][from_pos[1]]
        if not moving_piece:
            return False

        # Simular el movimiento
        original_piece = self.board[to_pos[0]][to_pos[1]]
        self.board[to_pos[0]][to_pos[1]] = moving_piece
        self.board[from_pos[0]][from_pos[1]] = None

        # Verificar si el rey sigue en jaque después del movimiento
        in_check = self.is_in_check(moving_piece.color)

        # Revertir el movimiento
        self.board[from_pos[0]][from_pos[1]] = moving_piece
        self.board[to_pos[0]][to_pos[1]] = original_piece

        return not in_check