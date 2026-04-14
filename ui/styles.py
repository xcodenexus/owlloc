COLORS = {
    "bg_primary":     "#0a0a0f",
    "bg_secondary":   "#111118",
    "bg_card":        "#16161f",
    "bg_hover":       "#1e1e2a",
    "accent":         "#ff9500",
    "accent_dim":     "#cc7700",
    "text_primary":   "#f0f0f0",
    "text_secondary": "#888899",
    "text_muted":     "#555566",
    "border":         "rgba(255,255,255,0.06)",
    "border_accent":  "rgba(255,149,0,0.25)",
    "success":        "#34c759",
    "error":          "#ff3b30",
    "warning":        "#ffcc00",
}

C = COLORS  # shorthand


def get_stylesheet() -> str:
    return f"""
/* ─── Global ─────────────────────────────────────────────── */
QWidget {{
    background-color: {C['bg_primary']};
    color: {C['text_primary']};
    font-family: 'Segoe UI';
    font-size: 13px;
}}

QMainWindow, QDialog {{
    background-color: {C['bg_primary']};
}}

/* ─── Sidebar ─────────────────────────────────────────────── */
#sidebar {{
    background-color: {C['bg_secondary']};
    border-right: 1px solid {C['border']};
    min-width: 260px;
    max-width: 260px;
}}

#logo-label {{
    font-size: 22px;
    font-weight: bold;
    color: {C['accent']};
    padding: 6px 0;
}}

#version-label {{
    font-size: 11px;
    color: {C['text_muted']};
}}

#divider {{
    background-color: {C['border']};
    max-height: 1px;
    min-height: 1px;
    margin: 8px 0;
}}

/* ─── Device card ─────────────────────────────────────────── */
#device-card {{
    background-color: {C['bg_card']};
    border: 1px solid {C['border']};
    border-radius: 10px;
    padding: 10px;
}}

#device-name {{
    font-size: 13px;
    font-weight: 600;
    color: {C['text_primary']};
}}

#device-detail {{
    font-size: 11px;
    color: {C['text_secondary']};
}}

#status-dot {{
    min-width: 8px;
    max-width: 8px;
    min-height: 8px;
    max-height: 8px;
    border-radius: 4px;
}}

#status-text {{
    font-size: 11px;
    color: {C['text_secondary']};
}}

/* ─── Nav buttons (sidebar) ────────────────────────────────── */
#nav-btn {{
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    color: {C['text_secondary']};
}}

#nav-btn:hover {{
    background-color: {C['bg_hover']};
    color: {C['text_primary']};
}}

#nav-btn[active="true"] {{
    background-color: {C['bg_card']};
    color: {C['accent']};
    border-left: 3px solid {C['accent']};
}}

/* ─── Right panel ─────────────────────────────────────────── */
#right-panel {{
    background-color: {C['bg_secondary']};
    border-left: 1px solid {C['border']};
    min-width: 300px;
    max-width: 300px;
}}

#panel-title {{
    font-size: 14px;
    font-weight: 600;
    color: {C['text_primary']};
    padding: 4px 0;
}}

#section-label {{
    font-size: 11px;
    color: {C['text_secondary']};
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* ─── Input fields ────────────────────────────────────────── */
QLineEdit {{
    background-color: {C['bg_card']};
    border: 1px solid {C['border']};
    border-radius: 8px;
    padding: 8px 12px;
    color: {C['text_primary']};
    font-family: Consolas, 'JetBrains Mono', monospace;
    font-size: 13px;
    selection-background-color: {C['accent']};
}}

QLineEdit:focus {{
    border-color: {C['border_accent']};
}}

QLineEdit::placeholder {{
    color: {C['text_muted']};
}}

/* ─── Buttons ─────────────────────────────────────────────── */
QPushButton {{
    border-radius: 8px;
    padding: 9px 16px;
    font-size: 13px;
    font-weight: 600;
    font-family: 'Segoe UI';
}}

/* Primary */
QPushButton#btn-primary {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ffaa22, stop:1 #ff9500);
    color: #000000;
    border: none;
}}
QPushButton#btn-primary:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ffbb44, stop:1 #ffaa22);
}}
QPushButton#btn-primary:pressed {{
    background: {C['accent_dim']};
}}
QPushButton#btn-primary:disabled {{
    background: {C['bg_card']};
    color: {C['text_muted']};
}}

/* Secondary */
QPushButton#btn-secondary {{
    background: transparent;
    color: {C['text_primary']};
    border: 1px solid {C['border']};
}}
QPushButton#btn-secondary:hover {{
    background-color: {C['bg_hover']};
    border-color: rgba(255,255,255,0.15);
}}
QPushButton#btn-secondary:pressed {{
    background-color: {C['bg_card']};
}}
QPushButton#btn-secondary:disabled {{
    color: {C['text_muted']};
}}

/* Danger */
QPushButton#btn-danger {{
    background: transparent;
    color: {C['error']};
    border: 1px solid {C['error']};
}}
QPushButton#btn-danger:hover {{
    background-color: rgba(255,59,48,0.1);
}}
QPushButton#btn-danger:pressed {{
    background-color: rgba(255,59,48,0.2);
}}
QPushButton#btn-danger:disabled {{
    color: {C['text_muted']};
    border-color: {C['text_muted']};
}}

/* ─── Scrollbars ──────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C['bg_hover']};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ─── List widgets ────────────────────────────────────────── */
QListWidget {{
    background: transparent;
    border: none;
    outline: none;
}}
QListWidget::item {{
    padding: 0;
    margin: 3px 0;
}}
QListWidget::item:selected {{
    background: transparent;
}}

/* ─── Slider ──────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 4px;
    background: {C['bg_card']};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 16px;
    height: 16px;
    background: {C['accent']};
    border-radius: 8px;
    margin: -6px 0;
}}
QSlider::sub-page:horizontal {{
    background: {C['accent']};
    border-radius: 2px;
}}

/* ─── Progress bar ────────────────────────────────────────── */
QProgressBar {{
    background: {C['bg_card']};
    border-radius: 4px;
    border: none;
    height: 6px;
    text-align: center;
    font-size: 0px;
}}
QProgressBar::chunk {{
    background: {C['accent']};
    border-radius: 4px;
}}

/* ─── Tooltip ─────────────────────────────────────────────── */
QToolTip {{
    background-color: {C['bg_card']};
    color: {C['text_primary']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 12px;
}}
"""
