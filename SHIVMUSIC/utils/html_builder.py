"""Telegram HTML captions used by the modern welcome screen.

Telegram renders the keyboard separately from the caption.  Keeping the
buttons in an InlineKeyboardMarkup (rather than embedding unsupported custom
HTML button tags) makes this work in current Telegram clients and Bot API
versions.
"""

def build_welcome_html(user_mention: str, bot_mention: str, bot_username: str) -> str:
    return (
        f"<tg-emoji emoji-id='5409368076447657845'>🌟</tg-emoji> <b>Greetings, {user_mention}!</b>\n\n"
        f"<tg-emoji emoji-id='5355051922862653659'>🤖</tg-emoji> <b>This is {bot_mention} — your premium music streaming companion.</b>\n\n"
        "<blockquote expandable>"
        "<b>✦ BOT INFORMATION ✦</b>\n"
        "<pre>"
        "┌────────────────┬──────────────────────────┐\n"
        "│ FEATURE        │ DETAILS                  │\n"
        "├────────────────┼──────────────────────────┤\n"
        "│ Streaming      │ High-quality, zero lag   │\n"
        "│ Speed          │ Instant response, 24×7   │\n"
        "│ Equalizer      │ 13 professional presets  │\n"
        "│ Platforms      │ YouTube, Spotify, Apple  │\n"
        "│ Availability   │ Active 24×7              │\n"
        "│ VIP Experience │ Premium controls &amp; FX    │\n"
        "└────────────────┴──────────────────────────┘"
        "</pre>"
        "</blockquote>\n\n"
        "<tg-emoji emoji-id='5188540541922480562'>❓</tg-emoji> <i>Tap Help to explore all available commands.</i>"
    )