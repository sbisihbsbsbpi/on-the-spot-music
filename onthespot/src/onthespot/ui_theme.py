"""
Modern Spotify-inspired UI Theme for OnTheSpot
Features: Dark theme, customizable accents, rounded corners, smooth animations
"""

# Default accent color (Spotify Green)
_custom_accent = None

def set_accent_color(color_hex):
    """Set a custom accent color for the theme."""
    global _custom_accent
    _custom_accent = color_hex

def get_accent_color():
    """Get the current accent color."""
    return _custom_accent or '#1DB954'

def _lighten_color(hex_color, percent=20):
    """Lighten a hex color by a percentage."""
    hex_color = hex_color.lstrip('#')
    r = min(255, int(hex_color[0:2], 16) + int(255 * percent / 100))
    g = min(255, int(hex_color[2:4], 16) + int(255 * percent / 100))
    b = min(255, int(hex_color[4:6], 16) + int(255 * percent / 100))
    return f'#{r:02x}{g:02x}{b:02x}'

def _darken_color(hex_color, percent=20):
    """Darken a hex color by a percentage."""
    hex_color = hex_color.lstrip('#')
    r = max(0, int(hex_color[0:2], 16) - int(255 * percent / 100))
    g = max(0, int(hex_color[2:4], 16) - int(255 * percent / 100))
    b = max(0, int(hex_color[4:6], 16) - int(255 * percent / 100))
    return f'#{r:02x}{g:02x}{b:02x}'

def get_colors():
    """Get the color palette with current accent color."""
    accent = get_accent_color()
    return {
        'background': '#121212',
        'background_alt': '#181818',
        'background_elevated': '#282828',
        'background_hover': '#333333',
        'surface': '#1a1a1a',
        'accent': accent,
        'accent_hover': _lighten_color(accent, 15),
        'accent_pressed': _darken_color(accent, 15),
        'text_primary': '#ffffff',
        'text_secondary': '#b3b3b3',
        'text_muted': '#727272',
        'border': '#404040',
        'success': accent,  # Use accent for success too
        'warning': '#f59e0b',
        'error': '#ef4444',
        'info': '#3b82f6',
        'progress_bg': '#404040',
    }

# For backwards compatibility
COLORS = get_colors()

def get_modern_theme():
    """Returns the complete modern Spotify-inspired stylesheet."""
    colors = get_colors()  # Get dynamic colors with custom accent
    return f"""
    /* ============================================ */
    /*  GLOBAL STYLES                              */
    /* ============================================ */
    
    QMainWindow, QWidget {{
        background-color: {colors['background']};
        color: {colors['text_primary']};
        font-size: 13px;
    }}
    
    /* ============================================ */
    /*  TABS                                       */
    /* ============================================ */
    
    QTabWidget::pane {{
        border: none;
        background-color: {colors['background']};
    }}
    
    QTabBar::tab {{
        background-color: {colors['background_alt']};
        color: {colors['text_secondary']};
        padding: 10px 20px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        border: none;
        font-weight: 500;
    }}
    
    QTabBar::tab:selected {{
        background-color: {colors['background_elevated']};
        color: {colors['text_primary']};
    }}
    
    QTabBar::tab:hover:!selected {{
        background-color: {colors['background_hover']};
        color: {colors['text_primary']};
    }}
    
    /* ============================================ */
    /*  BUTTONS                                    */
    /* ============================================ */

    QPushButton {{
        background-color: {colors['background_elevated']};
        color: {colors['text_primary']};
        border: none;
        border-radius: 3px;
        padding: 4px 10px;
        font-weight: 600;
        min-height: 16px;
    }}

    QPushButton:hover {{
        background-color: {colors['background_hover']};
    }}

    QPushButton:pressed {{
        background-color: {colors['border']};
    }}

    QPushButton:disabled {{
        background-color: {colors['surface']};
        color: {colors['text_muted']};
    }}
    
    /* Primary accent buttons */
    QPushButton#btn_search, QPushButton#btn_login_add {{
        background-color: {colors['accent']};
        color: #000000;
    }}
    
    QPushButton#btn_search:hover, QPushButton#btn_login_add:hover {{
        background-color: {colors['accent_hover']};
    }}
    
    QPushButton#btn_search:pressed, QPushButton#btn_login_add:pressed {{
        background-color: {colors['accent_pressed']};
    }}
    
    /* ============================================ */
    /*  INPUT FIELDS                               */
    /* ============================================ */
    
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {colors['background_elevated']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        border-radius: 3px;
        padding: 4px 8px;
        selection-background-color: {colors['accent']};
        selection-color: #000000;
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {colors['accent']};
    }}

    QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {{
        border-color: {colors['text_muted']};
    }}

    /* Disabled info labels (version, statistics) - clean flat look */
    QLineEdit:disabled {{
        background-color: {colors['background_alt']};
        color: {colors['text_primary']};
        border: none;
        border-radius: 4px;
        padding: 6px 12px;
    }}
    
    /* ============================================ */
    /*  COMBO BOX / DROPDOWN                       */
    /* ============================================ */
    
    QComboBox {{
        background-color: {colors['background_elevated']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        border-radius: 4px;
        padding: 6px 12px 6px 10px;
        min-height: 24px;
    }}

    QComboBox:hover {{
        border-color: {colors['text_muted']};
    }}

    QComboBox:focus {{
        border-color: {colors['accent']};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 30px;
        subcontrol-origin: padding;
        subcontrol-position: top right;
    }}

    QComboBox::down-arrow {{
        width: 12px;
        height: 12px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {colors['background_elevated']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        border-radius: 4px;
        selection-background-color: {colors['accent']};
        selection-color: #000000;
        padding: 4px;
    }}

    QComboBox QAbstractItemView::item {{
        min-height: 28px;
        padding: 4px 8px;
    }}

    QComboBox QAbstractItemView::item:selected {{
        background-color: {colors['accent']};
        color: #000000;
    }}
"""

def get_modern_theme_part2():
    """Returns part 2 of the theme (split due to size)."""
    colors = get_colors()  # Get dynamic colors with custom accent
    return f"""
    /* ============================================ */
    /*  TABLES                                     */
    /* ============================================ */
    
    QTableWidget, QTableView {{
        background-color: {colors['background']};
        alternate-background-color: {colors['background_alt']};
        color: {colors['text_primary']};
        border: none;
        border-radius: 4px;
        gridline-color: {colors['surface']};
        selection-background-color: {colors['background_hover']};
        selection-color: {colors['text_primary']};
    }}
    
    QTableWidget::item, QTableView::item {{
        padding: 8px;
        border: none;
    }}
    
    QTableWidget::item:selected, QTableView::item:selected {{
        background-color: {colors['background_hover']};
    }}
    
    QTableWidget::item:hover, QTableView::item:hover {{
        background-color: {colors['background_elevated']};
    }}
    
    QHeaderView::section {{
        background-color: {colors['surface']};
        color: {colors['text_secondary']};
        padding: 10px;
        border: none;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 11px;
    }}
    
    QHeaderView::section:hover {{
        background-color: {colors['background_elevated']};
    }}
    
    /* ============================================ */
    /*  SCROLLBARS                                 */
    /* ============================================ */
    
    QScrollBar:vertical {{
        background-color: {colors['background']};
        width: 10px;
        border-radius: 5px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {colors['border']};
        border-radius: 5px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {colors['text_muted']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background-color: {colors['background']};
        height: 10px;
        border-radius: 5px;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {colors['border']};
        border-radius: 5px;
        min-width: 30px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background-color: {colors['text_muted']};
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    
    /* ============================================ */
    /*  PROGRESS BARS                              */
    /* ============================================ */
    
    QProgressBar {{
        background-color: {colors['progress_bg']};
        border: none;
        border-radius: 3px;
        text-align: center;
        color: {colors['text_primary']};
        font-weight: 600;
        min-height: 20px;
    }}

    QProgressBar::chunk {{
        background-color: {colors['accent']};
        border-radius: 3px;
    }}
    
    /* ============================================ */
    /*  CHECKBOXES & RADIO BUTTONS                */
    /* ============================================ */
    
    QCheckBox {{
        color: {colors['text_primary']};
        spacing: 8px;
    }}
    
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 3px;
        border: 1px solid {colors['border']};
        background-color: {colors['background_elevated']};
    }}
    
    QCheckBox::indicator:checked {{
        background-color: {colors['accent']};
        border-color: {colors['accent']};
    }}
    
    QCheckBox::indicator:hover {{
        border-color: {colors['text_muted']};
    }}
    
    QRadioButton {{
        color: {colors['text_primary']};
        spacing: 6px;
        padding: 2px;
        background-color: transparent;
    }}

    QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 8px;
        border: 1px solid #888888;
        background-color: #2a2a2a;
    }}

    QRadioButton::indicator:hover {{
        border-color: {colors['accent']};
        background-color: #333333;
    }}

    QRadioButton::indicator:checked {{
        border: 2px solid {colors['accent']};
        background-color: {colors['accent']};
    }}
"""

def get_modern_theme_part3():
    """Returns part 3 of the theme."""
    colors = get_colors()  # Get dynamic colors with custom accent
    return f"""
    /* ============================================ */
    /*  LABELS                                     */
    /* ============================================ */
    
    QLabel {{
        color: {colors['text_primary']};
        background-color: transparent;
    }}
    
    /* ============================================ */
    /*  GROUP BOX                                  */
    /* ============================================ */
    
    QGroupBox {{
        background-color: {colors['background_alt']};
        border: 1px solid {colors['border']};
        border-radius: 4px;
        margin-top: 12px;
        padding-top: 10px;
        font-weight: 600;
    }}
    
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 5px 10px;
        color: {colors['text_primary']};
    }}
    
    /* ============================================ */
    /*  SPIN BOX                                   */
    /* ============================================ */
    
    QSpinBox, QDoubleSpinBox {{
        background-color: {colors['background_elevated']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        border-radius: 4px;
        padding: 6px 10px;
    }}
    
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {colors['accent']};
    }}
    
    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
        background-color: {colors['background_hover']};
        border: none;
        width: 20px;
    }}
    
    /* ============================================ */
    /*  SLIDER                                     */
    /* ============================================ */
    
    QSlider::groove:horizontal {{
        background-color: {colors['progress_bg']};
        height: 6px;
        border-radius: 3px;
    }}
    
    QSlider::handle:horizontal {{
        background-color: {colors['accent']};
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }}
    
    QSlider::handle:horizontal:hover {{
        background-color: {colors['accent_hover']};
    }}
    
    QSlider::sub-page:horizontal {{
        background-color: {colors['accent']};
        border-radius: 3px;
    }}
    
    /* ============================================ */
    /*  SCROLL AREA                                */
    /* ============================================ */
    
    QScrollArea {{
        background-color: {colors['background']};
        border: none;
    }}
    
    QScrollArea > QWidget > QWidget {{
        background-color: {colors['background']};
    }}
    
    /* ============================================ */
    /*  TOOLTIPS                                   */
    /* ============================================ */
    
    QToolTip {{
        background-color: {colors['background_elevated']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        border-radius: 4px;
        padding: 6px 10px;
    }}
    
    /* ============================================ */
    /*  STATUS BAR                                 */
    /* ============================================ */
    
    QStatusBar {{
        background-color: {colors['surface']};
        color: {colors['text_secondary']};
        border-top: 1px solid {colors['border']};
        padding: 4px;
    }}
    
    QStatusBar::item {{
        border: none;
    }}
    
    /* ============================================ */
    /*  MENU                                       */
    /* ============================================ */
    
    QMenu {{
        background-color: {colors['background_elevated']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        border-radius: 4px;
        padding: 4px;
    }}
    
    QMenu::item {{
        padding: 8px 20px;
        border-radius: 4px;
    }}
    
    QMenu::item:selected {{
        background-color: {colors['background_hover']};
    }}
    
    /* ============================================ */
    /*  DIALOG                                     */
    /* ============================================ */
    
    QDialog {{
        background-color: {colors['background']};
        color: {colors['text_primary']};
    }}
"""

def get_complete_theme():
    """Returns the complete stylesheet."""
    return get_modern_theme() + get_modern_theme_part2() + get_modern_theme_part3()


# Status badge styles for download queue
def get_status_style(status):
    """Returns the style for a given download status."""
    # Height controlled via stylesheet so hot-reload works
    # min/max-height constrains the label size
    base_style = '''
        padding: 0px 8px;
        border-radius: 3px;
        font-weight: bold;
        font-size: 11px;
        margin: 0px;
        min-height: 20px;
        max-height: 20px;
    '''

    styles = {
        'downloading': f'background-color: {COLORS["info"]}; color: #ffffff; {base_style}',
        'completed': f'background-color: {COLORS["success"]}; color: #ffffff; {base_style}',
        'downloaded': f'background-color: {COLORS["success"]}; color: #ffffff; {base_style}',
        'failed': f'background-color: {COLORS["error"]}; color: #ffffff; {base_style}',
        'waiting': f'background-color: {COLORS["warning"]}; color: #000000; {base_style}',
        'cancelled': f'background-color: {COLORS["text_muted"]}; color: #ffffff; {base_style}',
        'already exists': f'background-color: {COLORS["text_muted"]}; color: #ffffff; {base_style}',
        'rate limited': f'background-color: {COLORS["warning"]}; color: #000000; {base_style}',
        'converting': f'background-color: {COLORS["info"]}; color: #ffffff; {base_style}',
        'getting info': f'background-color: {COLORS["info"]}; color: #ffffff; {base_style}',
        'unavailable': f'background-color: {COLORS["error"]}; color: #ffffff; {base_style}',
    }

    if not status:
        return f'background-color: {COLORS["background_elevated"]}; color: {COLORS["text_primary"]}; {base_style}'

    status_lower = status.lower().strip()

    # Direct match first
    if status_lower in styles:
        return styles[status_lower]

    # Check for partial matches (e.g., "✓ Done · Wait 1m 30s")
    if 'done' in status_lower:
        return styles['completed']
    if 'wait' in status_lower:
        return f'background-color: #8b5cf6; color: #ffffff; {base_style}'  # Purple for stealth waiting
    if 'download' in status_lower:
        return styles['downloading']
    if 'convert' in status_lower:
        return styles['converting']
    if 'fail' in status_lower or 'error' in status_lower:
        return styles['failed']
    if 'cancel' in status_lower:
        return styles['cancelled']

    # Default style
    return f'background-color: {COLORS["background_elevated"]}; color: {COLORS["text_primary"]}; {base_style}'


def get_progress_bar_style(status='default'):
    """Returns progress bar style."""
    if status == 'completed':
        color = COLORS['success']
    elif status == 'failed':
        color = COLORS['error']
    elif status == 'waiting':
        color = COLORS['warning']
    else:
        color = COLORS['accent']

    return f"""
        QProgressBar {{
            background-color: {COLORS['progress_bg']};
            border: none;
            border-radius: 3px;
            text-align: center;
            color: white;
            font-size: 10px;
            font-weight: bold;
            min-height: 20px;
            max-height: 20px;
        }}
        QProgressBar::chunk {{
            background-color: {color};
            border-radius: 3px;
        }}
    """


def get_button_style():
    """Returns button styling for action buttons."""
    return f"""
        QPushButton {{
            background-color: {COLORS['background_elevated']};
            border: none;
            border-radius: 3px;
            padding: 2px;
        }}
        QPushButton:hover {{
            background-color: {COLORS['background_hover']};
        }}
        QPushButton:pressed {{
            background-color: {COLORS['accent']};
        }}
    """


def format_duration(ms):
    """Format duration in milliseconds to MM:SS or HH:MM:SS."""
    if not ms:
        return "--:--"
    try:
        total_seconds = int(ms) // 1000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"
    except (ValueError, TypeError):
        return "--:--"


def format_speed(bytes_per_sec):
    """Format download speed to human readable format."""
    if not bytes_per_sec or bytes_per_sec <= 0:
        return "-- KB/s"
    if bytes_per_sec >= 1024 * 1024:
        return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
    elif bytes_per_sec >= 1024:
        return f"{bytes_per_sec / 1024:.1f} KB/s"
    else:
        return f"{bytes_per_sec:.0f} B/s"

