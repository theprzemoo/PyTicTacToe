"""
TicTacToe — Two-player Tic-Tac-Toe desktop game
Style inspired by PyGenPass: dark theme, purple accents, smooth animations.
Author: theprzemoo
"""

import tkinter as tk
from tkinter import font as tkfont
import math

# ─────────────────────────────────────────────────────────────
#  COLOR PALETTE  (consistent with PyGenPass dark purple theme)
# ─────────────────────────────────────────────────────────────
C = {
    "bg":          "#1a1a2e",
    "surface":     "#16213e",
    "surface2":    "#0f3460",
    "accent":      "#7c3aed",
    "accent_hi":   "#a855f7",
    "teal":        "#06b6d4",
    "teal_dim":    "#164e63",
    "pink":        "#f472b6",
    "pink_dim":    "#4d1435",
    "text":        "#e2e8f0",
    "muted":       "#64748b",
    "gold":        "#fbbf24",
    "gold_dim":    "#78350f",
    "cell":        "#0d1526",
    "cell_hi_x":   "#1e1030",
    "cell_hi_o":   "#051a25",
    "border":      "#1e293b",
    "sep":         "#334155",
}

# ─────────────────────────────────────────────────────────────
#  HELPERS — colour arithmetic (all Tkinter-safe #rrggbb only)
# ─────────────────────────────────────────────────────────────
def hex_to_rgb(h):
    h = h.lstrip("#")
    return int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)

def rgb_to_hex(r, g, b):
    return "#{:02x}{:02x}{:02x}".format(r, g, b)

def lerp_color(c1, c2, t):
    """Linear interpolation between two #rrggbb colours. t in [0,1]."""
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    return rgb_to_hex(
        int(r1 + (r2 - r1) * t),
        int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t),
    )

# ─────────────────────────────────────────────────────────────
#  GAME LOGIC  (pure functions, zero UI)
# ─────────────────────────────────────────────────────────────
WIN_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (0, 3, 6), (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6),
]

def check_winner(board):
    """Return (winner_symbol, winning_triple) or (None, None)."""
    for a, b, c in WIN_LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a], (a, b, c)
    return None, None

def is_draw(board):
    return all(cell for cell in board)

def other_player(p):
    return "O" if p == "X" else "X"

# ─────────────────────────────────────────────────────────────
#  ANIMATED BUTTON
# ─────────────────────────────────────────────────────────────
class AnimButton(tk.Label):
    """Smooth colour-interpolated hover button."""

    def __init__(self, parent, text, command,
                 bg_n, bg_h, fg="#e2e8f0", font=None, px=24, py=10):
        super().__init__(parent, text=text, bg=bg_n, fg=fg,
                         font=font, padx=px, pady=py,
                         cursor="hand2", relief="flat")
        self._bg_n = bg_n
        self._bg_h = bg_h
        self._cmd  = command
        self.bind("<Enter>",    lambda _: self._anim(bg_n, bg_h))
        self.bind("<Leave>",    lambda _: self._anim(bg_h, bg_n))
        self.bind("<Button-1>", self._click)

    def _click(self, _):
        orig = int(self.cget("pady"))
        self.config(pady=max(orig - 3, 2))
        self.after(90,  lambda: self.config(pady=orig))
        if self._cmd:
            self.after(70, self._cmd)

    def _anim(self, src, dst, steps=8, delay=14):
        def frame(i=0):
            if i > steps:
                self.config(bg=dst)
                return
            self.config(bg=lerp_color(src, dst, i / steps))
            self.after(delay, lambda: frame(i + 1))
        frame()

# ─────────────────────────────────────────────────────────────
#  CELL  (one square of the board)
# ─────────────────────────────────────────────────────────────
class Cell:
    SIZE = 158  # pixels

    def __init__(self, parent, idx, on_click):
        self.idx = idx
        self._on_click = on_click

        self.canvas = tk.Canvas(parent, width=self.SIZE, height=self.SIZE,
                                bg=C["cell"], highlightthickness=0,
                                cursor="hand2")
        self.lbl = tk.Label(self.canvas, text="", bg=C["cell"],
                            fg=C["text"], font=None)
        self.lbl.place(relx=0.5, rely=0.5, anchor="center")

        for w in (self.canvas, self.lbl):
            w.bind("<Button-1>", lambda e: self._on_click(self.idx))
            w.bind("<Enter>",    lambda e: self._hover(True))
            w.bind("<Leave>",    lambda e: self._hover(False))

    def grid(self, **kw):
        self.canvas.grid(**kw)

    # ── background helper ──
    def set_bg(self, color):
        self.canvas.config(bg=color)
        self.lbl.config(bg=color)

    # ── hover ghost preview ──
    def _hover(self, entering):
        app = self.canvas.winfo_toplevel()
        if not hasattr(app, "board"):
            return
        if app.game_over or app.board[self.idx]:
            return
        p = app.current_player
        if entering:
            hi = C["cell_hi_x"] if p == "X" else C["cell_hi_o"]
            self.set_bg(hi)
            ghost = lerp_color(C["pink"] if p == "X" else C["teal"],
                               C["cell"], 0.52)
            self.lbl.config(text=p, fg=ghost)
        else:
            self.set_bg(C["cell"])
            self.lbl.config(text="")

    # ── bounce-in symbol ──
    def place_symbol(self, symbol, font_factory):
        color = C["pink"] if symbol == "X" else C["teal"]
        sizes = [12, 22, 34, 46, 58, 52, 48, 50, 48]
        self.set_bg(C["cell"])
        app = self.canvas.winfo_toplevel()

        def frame(i=0):
            if i >= len(sizes):
                self.lbl.config(font=font_factory(48), text=symbol, fg=color)
                return
            self.lbl.config(font=font_factory(sizes[i]), text=symbol, fg=color)
            app.after(22, lambda: frame(i + 1))

        frame()

    # ── reject flash (red blink) ──
    def flash_reject(self):
        app = self.canvas.winfo_toplevel()
        seq = ["#2d0a0a", C["cell"], "#2d0a0a", C["cell"]]
        def step(i=0):
            if i >= len(seq):
                return
            self.set_bg(seq[i])
            app.after(55, lambda: step(i + 1))
        step()

    # ── winning gold ripple + pulse ──
    def highlight_win(self, app, delay):
        ripple = [C["cell"], "#2a1f00", "#4a3800", "#6b5200",
                  "#9a7800", C["gold_dim"], C["gold"], C["gold_dim"]]

        def show_ripple(i=0):
            if i >= len(ripple):
                pulse(0)
                return
            bg = ripple[i]
            self.set_bg(bg)
            self.lbl.config(fg=C["gold"], bg=bg)
            app.after(28, lambda: show_ripple(i + 1))

        def pulse(i=0):
            if i > 16:
                return
            t = (math.sin(i * math.pi / 4) + 1) / 2
            bg = lerp_color(C["gold_dim"], "#3d2d00", t)
            fg = lerp_color(C["gold"], "#ffe066", t)
            self.set_bg(bg)
            self.lbl.config(fg=fg, bg=bg)
            app.after(130, lambda: pulse(i + 1))

        app.after(delay, show_ripple)

    # ── draw wave-grey ──
    def grey_out(self, app, delay):
        symbol = self.lbl.cget("text")
        if not symbol:
            return
        orig = C["pink"] if symbol == "X" else C["teal"]
        steps = 10
        def fade(i=0):
            if i > steps:
                return
            self.lbl.config(fg=lerp_color(orig, C["muted"], i / steps))
            app.after(30, lambda: fade(i + 1))
        app.after(delay, fade)

    # ── reset to blank ──
    def reset(self):
        self.set_bg(C["cell"])
        self.lbl.config(text="", fg=C["text"])

# ─────────────────────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────────────────────
class TicTacToeApp(tk.Tk):

    WIN_W = 620
    WIN_H = 860

    def __init__(self):
        super().__init__()
        self.title("TicTacToe")
        self.resizable(False, False)
        self.configure(bg=C["bg"])

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry("{}x{}+{}+{}".format(
            self.WIN_W, self.WIN_H,
            (sw - self.WIN_W) // 2,
            (sh - self.WIN_H) // 2,
        ))

        # Game state
        self.board = [""] * 9
        self.current_player = "X"
        self.game_over = False
        self.scores = {"X": 0, "O": 0, "D": 0}

        self._init_fonts()
        self._set_icon()
        self._build_ui()

        # Fade in on startup
        self.attributes("-alpha", 0.0)
        self._fade_window(0.0, 1.0, steps=20, delay=14)

    # ─────────────────────────────────────
    #  ICON  (programmatic pixel-art)
    # ─────────────────────────────────────
    def _set_icon(self):
        try:
            img = tk.PhotoImage(width=32, height=32)
            for y in range(32):
                for x in range(32):
                    col = "#7c3aed"
                    # X in left half
                    if x < 15:
                        lx = x - 7
                        ly = y - 16
                        if abs(abs(lx) - abs(ly)) <= 1 and abs(lx) < 7:
                            col = "#f472b6"
                    # O in right half
                    else:
                        rx = x - 24
                        ry = y - 16
                        dist = math.sqrt(rx*rx + ry*ry)
                        if 5.5 <= dist <= 8.5:
                            col = "#06b6d4"
                    img.put(col, (x, y))
            self.iconphoto(True, img)
        except Exception:
            pass

    # ─────────────────────────────────────
    #  FONTS
    # ─────────────────────────────────────
    def _init_fonts(self):
        self.f = {
            "title":   tkfont.Font(family="Segoe UI", size=26, weight="bold"),
            "sub":     tkfont.Font(family="Segoe UI", size=11),
            "status":  tkfont.Font(family="Segoe UI", size=14, weight="bold"),
            "score_n": tkfont.Font(family="Segoe UI", size=24, weight="bold"),
            "score_l": tkfont.Font(family="Segoe UI", size=10),
            "btn":     tkfont.Font(family="Segoe UI", size=11, weight="bold"),
            "footer":  tkfont.Font(family="Segoe UI", size=9),
        }

    def cell_font(self, size):
        return tkfont.Font(family="Segoe UI", size=size, weight="bold")

    # ─────────────────────────────────────
    #  BUILD UI
    # ─────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=C["bg"])
        hdr.pack(pady=(30, 0))
        tk.Label(hdr, text="✦  TicTacToe  ✦",
                 font=self.f["title"], fg=C["accent_hi"], bg=C["bg"]).pack()
        tk.Label(hdr, text="two players · one screen",
                 font=self.f["sub"],   fg=C["muted"],     bg=C["bg"]).pack(pady=(3, 0))

        # Separator
        tk.Frame(self, height=2, bg=C["accent"]).pack(fill="x", padx=44, pady=(16, 0))

        # Scoreboard
        self._build_scoreboard()

        # Player bar (coloured strip)
        self._player_bar = tk.Frame(self, height=4, bg=C["pink"])
        self._player_bar.pack(fill="x", padx=44)

        # Status canvas (slide-in text)
        self._status_cv = tk.Canvas(self, height=50, bg=C["surface"],
                                     highlightthickness=0)
        self._status_cv.pack(fill="x", padx=44, pady=(10, 0))

        # Board
        self._build_board()

        # Buttons
        self._build_buttons()

        # Footer
        tk.Label(self, text="made with ♥  —  theprzemoo",
                 font=self.f["footer"], fg=C["muted"], bg=C["bg"]
                 ).pack(side="bottom", pady=12)

    def _build_scoreboard(self):
        sb = tk.Frame(self, bg=C["surface2"])
        sb.pack(fill="x", padx=44, pady=(14, 0))

        def col(label_text, score_color):
            f = tk.Frame(sb, bg=C["surface2"])
            f.pack(side="left", expand=True, pady=14)
            lbl = tk.Label(f, text="0", font=self.f["score_n"],
                           fg=score_color, bg=C["surface2"])
            lbl.pack()
            tk.Label(f, text=label_text, font=self.f["score_l"],
                     fg=C["muted"], bg=C["surface2"]).pack()
            return lbl

        self._lbl_x = col("Player X", C["pink"])
        self._lbl_d = col("Draws",    C["muted"])
        self._lbl_o = col("Player O", C["teal"])

    def _build_board(self):
        outer = tk.Frame(self, bg=C["accent"], padx=3, pady=3)
        outer.pack(padx=44, pady=(14, 0))
        inner = tk.Frame(outer, bg=C["sep"])
        inner.pack()

        self._cells = []
        for i in range(9):
            row, col_i = divmod(i, 3)
            cell = Cell(inner, i, self._cell_clicked)
            cell.lbl.config(font=self.cell_font(48))
            cell.grid(row=row, column=col_i, padx=2, pady=2)
            self._cells.append(cell)

    def _build_buttons(self):
        row = tk.Frame(self, bg=C["bg"])
        row.pack(pady=(20, 0))

        AnimButton(row, "⟳   New Game", self._new_game,
                   bg_n=C["accent"], bg_h=C["accent_hi"],
                   fg=C["text"], font=self.f["btn"], px=30, py=12
                   ).pack(side="left", padx=8)

        AnimButton(row, "✕   Reset Scores", self._reset_scores,
                   bg_n=C["surface2"], bg_h=C["border"],
                   fg=C["muted"], font=self.f["btn"], px=22, py=12
                   ).pack(side="left", padx=8)

    # ─────────────────────────────────────
    #  GAME FLOW
    # ─────────────────────────────────────
    def _cell_clicked(self, idx):
        if self.game_over or self.board[idx]:
            self._cells[idx].flash_reject()
            return

        self.board[idx] = self.current_player
        self._cells[idx].place_symbol(self.current_player, self.cell_font)

        winner, combo = check_winner(self.board)
        if winner:
            self.game_over = True
            self.scores[winner] += 1
            self._on_win(winner, combo)
        elif is_draw(self.board):
            self.game_over = True
            self.scores["D"] += 1
            self._on_draw()
        else:
            self.current_player = other_player(self.current_player)
            self._refresh_status()
            self._set_player_bar()

    def _on_win(self, winner, combo):
        for i, idx in enumerate(combo):
            self._cells[idx].highlight_win(self, i * 130)
        color = C["pink"] if winner == "X" else C["teal"]
        self.after(520, lambda: self._slide_status(
            "🎉  Player {} wins!".format(winner), color))
        self.after(520, lambda: self._animate_score(winner))
        self._anim_player_bar(color)

    def _on_draw(self):
        for i, cell in enumerate(self._cells):
            cell.grey_out(self, i * 55)
        self.after(420, lambda: self._slide_status("🤝  It's a draw!", C["muted"]))
        self.after(420, lambda: self._animate_score("D"))
        self._anim_player_bar(C["muted"])

    def _new_game(self):
        self._fade_cells(out=True, callback=self._do_reset)

    def _do_reset(self):
        self.board = [""] * 9
        self.game_over = False
        for cell in self._cells:
            cell.reset()
        self._refresh_status()
        self._set_player_bar()
        self._fade_cells(out=False, callback=None)

    def _reset_scores(self):
        self.scores = {"X": 0, "O": 0, "D": 0}
        for lbl in (self._lbl_x, self._lbl_o, self._lbl_d):
            lbl.config(text="0")
        self._new_game()

    # ─────────────────────────────────────
    #  STATUS  (slide-in canvas text)
    # ─────────────────────────────────────
    def _refresh_status(self):
        color = C["pink"] if self.current_player == "X" else C["teal"]
        self._slide_status("▶  Player {}'s turn".format(self.current_player), color)

    def _slide_status(self, text, color):
        cv = self._status_cv
        self.update_idletasks()
        w = cv.winfo_width() or (self.WIN_W - 88)
        cx = w // 2
        cy = 25

        def frame(x):
            cv.delete("all")
            cv.create_rectangle(0, 0, w, 50, fill=C["surface"], outline="")
            cv.create_text(x, cy, text=text, fill=color,
                           font=self.f["status"], anchor="center")
            if x < cx:
                nxt = min(x + (cx + w // 2) // 8, cx)
                cv.after(15, lambda: frame(nxt))

        frame(-cx // 3)

    # ─────────────────────────────────────
    #  PLAYER BAR
    # ─────────────────────────────────────
    def _set_player_bar(self):
        color = C["pink"] if self.current_player == "X" else C["teal"]
        self._player_bar.config(bg=color)

    def _anim_player_bar(self, target):
        src = self._player_bar.cget("bg")
        steps = 12
        def frame(i=0):
            if i > steps:
                self._player_bar.config(bg=target)
                return
            self._player_bar.config(bg=lerp_color(src, target, i / steps))
            self.after(16, lambda: frame(i + 1))
        frame()

    # ─────────────────────────────────────
    #  SCORE COUNT-UP
    # ─────────────────────────────────────
    def _animate_score(self, key):
        lbl   = {"X": self._lbl_x, "O": self._lbl_o, "D": self._lbl_d}[key]
        color = {"X": C["pink"],   "O": C["teal"],    "D": C["muted"]}[key]
        current = int(lbl.cget("text"))
        target  = self.scores[key]

        def count(n):
            lbl.config(text=str(n), fg=C["gold"])
            if n < target:
                self.after(80, lambda: count(n + 1))
            else:
                self.after(500, lambda: lbl.config(fg=color))

        count(current)

    # ─────────────────────────────────────
    #  BOARD FADE (reset transition)
    # ─────────────────────────────────────
    def _fade_cells(self, out, callback, steps=8, delay=20):
        src = C["cell"] if out else "#000000"
        dst = "#000000" if out else C["cell"]

        def frame(i=0):
            if i > steps:
                if out and callback:
                    callback()
                return
            bg = lerp_color(src, dst, i / steps)
            for cell in self._cells:
                cell.set_bg(bg)
                if out:
                    # hide text smoothly
                    cell.lbl.config(fg=lerp_color(
                        cell.lbl.cget("fg"), bg, i / steps
                    ) if cell.lbl.cget("text") else bg)
            self.after(delay, lambda: frame(i + 1))

        frame()

    # ─────────────────────────────────────
    #  WINDOW FADE-IN
    # ─────────────────────────────────────
    def _fade_window(self, alpha, target, steps, delay):
        if alpha >= target:
            self.attributes("-alpha", target)
            self._refresh_status()
            self._set_player_bar()
            return
        self.attributes("-alpha", alpha)
        nxt = min(alpha + target / steps, target)
        self.after(delay, lambda: self._fade_window(nxt, target, steps, delay))


# ─────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = TicTacToeApp()
    app.mainloop()
