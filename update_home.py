from pathlib import Path
import re
import shutil

# ============================================================
# EchoShield - SAFE HOME PAGE UPDATER
# Backend is NEVER modified.
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"
CLEAN_BACKUP = BASE_DIR / "index_clean_backup.html"

print("=" * 65)
print("EchoShield Safe Home Page Updater")
print("=" * 65)

# ------------------------------------------------------------
# 1. Check files
# ------------------------------------------------------------

if not CLEAN_BACKUP.exists():
    print("ERROR: index_clean_backup.html was not found.")
    print("Nothing was changed.")
    raise SystemExit(1)

# Always start from the clean backup.
html = CLEAN_BACKUP.read_text(encoding="utf-8")

# ------------------------------------------------------------
# 2. Safety checks BEFORE modification
# ------------------------------------------------------------

required_features = [
    'id="live"',
    'id="calls"',
    'id="scanner"',
    'id="fraud"',
    'id="assistant"',
    'id="reports"',
    'id="settings"',
]

missing = [x for x in required_features if x not in html]

if missing:
    print("ERROR: Clean backup is missing existing frontend features:")
    for item in missing:
        print("  -", item)
    print("Nothing was changed.")
    raise SystemExit(1)

# ------------------------------------------------------------
# 3. Create another safety copy
# ------------------------------------------------------------

shutil.copy2(CLEAN_BACKUP, INDEX_FILE)

# ------------------------------------------------------------
# 4. Home HTML
#
# IMPORTANT:
# We use DIVs inside Home instead of nested SECTION tags.
# This avoids broken HTML replacement.
# ------------------------------------------------------------

home_html = r'''
<section id="home" class="page active">

    <div class="eh-home-header">

        <div class="eh-home-heading">
            <div class="eh-home-eyebrow">ECHOSHIELD SECURITY CENTER</div>

            <h1>Good Morning!</h1>

            <p>
                Your security overview for today.
            </p>
        </div>

        <div class="eh-protection-summary">

            <div class="eh-protection-icon">🛡</div>

            <div>
                <div class="eh-protection-title">You're Protected</div>
                <div class="eh-protection-subtitle">
                    Protection is active
                </div>
                <div class="eh-last-checked">
                    Last checked: Just now
                </div>
            </div>

            <button
                type="button"
                class="eh-primary-btn"
                onclick="ehToggleProtectionPanel()">
                View Protection
            </button>

        </div>

    </div>


    <!-- ======================================================
         PROTECTION STATUS
         ====================================================== -->

    <div
        id="eh-protection-panel"
        class="eh-section eh-protection-panel"
        style="display:none;">

        <div class="eh-section-header">

            <div>
                <div class="eh-section-label">SYSTEM STATUS</div>
                <h2>Protection Status</h2>
            </div>

            <div class="eh-active-badge">
                <span></span>
                Protection Active
            </div>

        </div>


        <div class="eh-protection-grid">

            <div class="eh-protection-card">
                <div class="eh-system-icon">🛡</div>
                <div>
                    <strong>Spam Detection</strong>
                    <span>Active</span>
                </div>
                <div class="eh-status-dot"></div>
            </div>


            <div class="eh-protection-card">
                <div class="eh-system-icon">🔍</div>
                <div>
                    <strong>Scam Detection</strong>
                    <span>Active</span>
                </div>
                <div class="eh-status-dot"></div>
            </div>


            <div class="eh-protection-card">
                <div class="eh-system-icon">🎙</div>
                <div>
                    <strong>Voice Protection</strong>
                    <span>Active</span>
                </div>
                <div class="eh-status-dot"></div>
            </div>


            <div class="eh-protection-card">
                <div class="eh-system-icon">💳</div>
                <div>
                    <strong>Transaction Protection</strong>
                    <span>Active</span>
                </div>
                <div class="eh-status-dot"></div>
            </div>

        </div>


        <div class="eh-protection-footer">
            <span>4/4 Protections Active</span>
            <span class="eh-footer-check">✓ All systems operational</span>
        </div>

    </div>


    <!-- ======================================================
         TODAY'S SECURITY
         ====================================================== -->

    <div class="eh-section">

        <div class="eh-section-header">

            <div>
                <div class="eh-section-label">TODAY</div>
                <h2>Today's Security</h2>
            </div>

        </div>


        <div class="eh-stat-grid">

            <div class="eh-stat-card">
                <div class="eh-stat-icon">📞</div>
                <div class="eh-stat-value">12</div>
                <div class="eh-stat-name">Calls Analyzed</div>
            </div>


            <div class="eh-stat-card">
                <div class="eh-stat-icon">⚠</div>
                <div class="eh-stat-value">1</div>
                <div class="eh-stat-name">Suspicious Calls</div>
            </div>


            <div class="eh-stat-card">
                <div class="eh-stat-icon">🚫</div>
                <div class="eh-stat-value">0</div>
                <div class="eh-stat-name">Blocked</div>
            </div>


            <div class="eh-stat-card">
                <div class="eh-stat-icon">✓</div>
                <div class="eh-stat-value eh-none-value">None</div>
                <div class="eh-stat-name">High-Risk Actions</div>
            </div>

        </div>

    </div>


    <!-- ======================================================
         QUICK ACTIONS
         ====================================================== -->

    <div class="eh-section">

        <div class="eh-section-header">

            <div>
                <div class="eh-section-label">SHORTCUTS</div>
                <h2>Quick Actions</h2>
            </div>

        </div>


        <div class="eh-action-grid">

            <button
                type="button"
                class="eh-action-card"
                onclick="startRealTimeProtection()">

                <span class="eh-action-icon">🛡</span>

                <span>
                    <strong>Live Protect</strong>
                    <small>Start real-time protection</small>
                </span>

                <span class="eh-action-arrow">→</span>

            </button>


            <button
                type="button"
                class="eh-action-card"
                onclick="ehOpenSecureCalls()">

                <span class="eh-action-icon">📞</span>

                <span>
                    <strong>Secure Call</strong>
                    <small>Open secure calling</small>
                </span>

                <span class="eh-action-arrow">→</span>

            </button>


            <button
                type="button"
                class="eh-action-card"
                onclick="ehOpenVoiceScanner()">

                <span class="eh-action-icon">🎙</span>

                <span>
                    <strong>Scan Voice</strong>
                    <small>Analyze a voice recording</small>
                </span>

                <span class="eh-action-arrow">→</span>

            </button>


            <button
                type="button"
                class="eh-action-card"
                onclick="ehCheckNumber()">

                <span class="eh-action-icon">🔎</span>

                <span>
                    <strong>Check Number</strong>
                    <small>Check a suspicious caller</small>
                </span>

                <span class="eh-action-arrow">→</span>

            </button>

        </div>

    </div>


    <!-- ======================================================
         RECENT ACTIVITY
         ====================================================== -->

    <div class="eh-section">

        <div class="eh-section-header">

            <div>
                <div class="eh-section-label">SECURITY LOG</div>
                <h2>Recent Activity</h2>
            </div>

        </div>


        <div class="eh-activity-list">


            <button
                type="button"
                class="eh-activity-item eh-high"
                onclick="ehShowCallDetails('scam')">

                <div class="eh-activity-status">
                    🔴
                </div>

                <div class="eh-activity-main">

                    <strong>Potential Scam Detected</strong>

                    <span>
                        +91 XXXXXXX23
                    </span>

                    <small>
                        Payment request detected
                    </small>

                </div>

                <div class="eh-activity-time">
                    2 min ago
                </div>

            </button>


            <button
                type="button"
                class="eh-activity-item eh-medium"
                onclick="ehShowCallDetails('suspicious')">

                <div class="eh-activity-status">
                    🟠
                </div>

                <div class="eh-activity-main">

                    <strong>Suspicious Caller</strong>

                    <span>
                        +91 XXXXXXX29
                    </span>

                    <small>
                        Unknown business number
                    </small>

                </div>

                <div class="eh-activity-time">
                    25 min ago
                </div>

            </button>


            <button
                type="button"
                class="eh-activity-item eh-safe"
                onclick="ehShowCallDetails('verified')">

                <div class="eh-activity-status">
                    🟢
                </div>

                <div class="eh-activity-main">

                    <strong>Verified Caller</strong>

                    <span>
                        ABC Bank
                    </span>

                    <small>
                        Verified business
                    </small>

                </div>

                <div class="eh-activity-time">
                    1 hr ago
                </div>

            </button>


        </div>


        <button
            type="button"
            class="eh-view-all"
            onclick="ehViewAllActivity()">

            View All Activity
            <span>→</span>

        </button>

    </div>


    <!-- ======================================================
         CALL SECURITY DETAILS
         ====================================================== -->

    <div
        id="eh-call-details"
        class="eh-details-overlay"
        style="display:none;">

        <div class="eh-details-card">

            <button
                type="button"
                class="eh-close-btn"
                onclick="ehCloseCallDetails()">
                ×
            </button>


            <div id="eh-detail-risk" class="eh-detail-risk">
                HIGH RISK
            </div>


            <h2 id="eh-detail-title">
                Potential Scam Detected
            </h2>


            <div id="eh-detail-caller" class="eh-detail-caller">
                Caller: +91 XXXXXXX23
            </div>


            <div class="eh-risk-score">

                <div>
                    <span>Risk Score</span>
                    <strong id="eh-detail-score">87/100</strong>
                </div>

                <div class="eh-risk-bar">
                    <div id="eh-risk-fill"></div>
                </div>

            </div>


            <div class="eh-detail-question">
                Why was this call flagged?
            </div>


            <div id="eh-detail-reasons" class="eh-detail-reasons">

                <div>Unknown caller</div>
                <div>14 spam reports</div>
                <div>Suspicious language detected</div>
                <div>Possible impersonation</div>
                <div>Payment request detected</div>
                <div>AI-generated voice probability: 82%</div>

            </div>


            <div class="eh-recommended">

                <span>Recommended Action</span>

                <strong>
                    Block this caller
                </strong>

            </div>


            <div class="eh-detail-actions">

                <button
                    type="button"
                    onclick="ehDetailAction('verify')">
                    Verify
                </button>

                <button
                    type="button"
                    onclick="ehDetailAction('block')"
                    class="eh-danger-btn">
                    Block
                </button>

                <button
                    type="button"
                    onclick="ehDetailAction('report')">
                    Report
                </button>

            </div>

        </div>

    </div>

</section>
'''

# ------------------------------------------------------------
# 5. Replace ONLY the top-level Home section
#
# We look for:
# <section id="home"...>
#
# and stop at the next section having an id.
#
# Nested Home divs cannot accidentally terminate this replacement.
# ------------------------------------------------------------

home_pattern = re.compile(
    r'<section\s+id=["\']home["\'][^>]*>.*?(?=<section\s+id=["\'][^"\']+["\'])',
    re.IGNORECASE | re.DOTALL
)

match = home_pattern.search(html)

if not match:
    print("ERROR: Could not safely locate the Home section.")
    print("Nothing was changed.")
    raise SystemExit(1)

html = html[:match.start()] + home_html + "\n\n" + html[match.end():]

# ------------------------------------------------------------
# 6. Remove ONLY old Home CSS
#
# We NEVER delete an entire style block.
# ------------------------------------------------------------

old_marker = "EchoShield Professional Home Dashboard"

marker_index = html.find(old_marker)

if marker_index != -1:

    style_start = html.rfind("<style", 0, marker_index)
    style_end = html.find("</style>", marker_index)

    if style_start != -1 and style_end != -1:

        # Preserve everything before the Home CSS marker.
        before = html[:marker_index]

        # Preserve everything after the old Home CSS.
        after = html[style_end:]

        html = before + after

# Remove the known broken nested selector if still present.
html = html.replace(
    '#home .eh-home-header {\n\n.eh-home-header {',
    '.eh-home-header {'
)

# ------------------------------------------------------------
# 7. New Home CSS
# ------------------------------------------------------------

home_css = r'''
/* ============================================================
   EchoShield Home Dashboard - Safe Dedicated Styles
   ============================================================ */

#home .eh-home-header {
    display: flex;
    align-items: stretch;
    justify-content: space-between;
    gap: 24px;
    margin-bottom: 24px;
}

#home .eh-home-heading {
    flex: 1;
    padding: 8px 0;
}

#home .eh-home-eyebrow,
#home .eh-section-label {
    color: #6f8ba8;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.5px;
    margin-bottom: 8px;
}

#home .eh-home-heading h1 {
    font-size: 32px;
    line-height: 1.15;
    margin-bottom: 8px;
    color: #f4f8fc;
}

#home .eh-home-heading p {
    color: #91a5b9;
    font-size: 14px;
}

#home .eh-protection-summary {
    min-width: 430px;
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 18px 20px;
    border: 1px solid #21405c;
    border-radius: 16px;
    background: linear-gradient(135deg, #0b1c2d, #0d2437);
}

#home .eh-protection-icon {
    width: 48px;
    height: 48px;
    display: grid;
    place-items: center;
    border-radius: 14px;
    background: #123a4e;
    font-size: 23px;
}

#home .eh-protection-title {
    font-size: 17px;
    font-weight: 800;
    color: #f2f8ff;
}

#home .eh-protection-subtitle {
    margin-top: 3px;
    font-size: 13px;
    color: #65d6a0;
}

#home .eh-last-checked {
    margin-top: 4px;
    font-size: 11px;
    color: #7890a7;
}

#home .eh-primary-btn {
    margin-left: auto;
    border: 1px solid #315a79;
    border-radius: 9px;
    padding: 10px 14px;
    background: #12334b;
    color: #eaf5ff;
    cursor: pointer;
    font-weight: 700;
    white-space: nowrap;
}

#home .eh-primary-btn:hover {
    background: #17415e;
}

#home .eh-section {
    margin-top: 24px;
}

#home .eh-section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 13px;
}

#home .eh-section-header h2 {
    font-size: 19px;
    color: #eaf2fa;
}

#home .eh-protection-panel {
    padding: 20px;
    border: 1px solid #24455e;
    border-radius: 16px;
    background: #0a1827;
}

#home .eh-active-badge {
    display: flex;
    align-items: center;
    gap: 7px;
    color: #6ee0aa;
    font-size: 12px;
    font-weight: 700;
}

#home .eh-active-badge span,
#home .eh-status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #54d69b;
    box-shadow: 0 0 9px rgba(84,214,155,.45);
}

#home .eh-protection-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
}

#home .eh-protection-card {
    min-height: 82px;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 14px;
    border: 1px solid #1b344b;
    border-radius: 12px;
    background: #0d1d2d;
}

#home .eh-system-icon {
    font-size: 21px;
}

#home .eh-protection-card strong {
    display: block;
    color: #eaf3fb;
    font-size: 13px;
}

#home .eh-protection-card span {
    display: block;
    margin-top: 4px;
    color: #61d69d;
    font-size: 11px;
}

#home .eh-status-dot {
    margin-left: auto;
    flex-shrink: 0;
}

#home .eh-protection-footer {
    display: flex;
    justify-content: space-between;
    margin-top: 14px;
    padding-top: 14px;
    border-top: 1px solid #1b344b;
    color: #9bb0c4;
    font-size: 12px;
}

#home .eh-footer-check {
    color: #67dca5;
}

#home .eh-stat-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 13px;
}

#home .eh-stat-card {
    padding: 18px;
    border: 1px solid #1b344b;
    border-radius: 14px;
    background: #0b1928;
}

#home .eh-stat-icon {
    font-size: 20px;
    margin-bottom: 12px;
}

#home .eh-stat-value {
    font-size: 26px;
    font-weight: 800;
    color: #f0f6fc;
}

#home .eh-none-value {
    font-size: 20px;
    padding-top: 4px;
}

#home .eh-stat-name {
    margin-top: 5px;
    color: #8198ae;
    font-size: 12px;
}

#home .eh-action-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 13px;
}

#home .eh-action-card {
    min-height: 86px;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px;
    text-align: left;
    border: 1px solid #1d3a52;
    border-radius: 14px;
    background: #0b1928;
    color: #eaf3fb;
    cursor: pointer;
    transition: .18s ease;
}

#home .eh-action-card:hover {
    transform: translateY(-2px);
    border-color: #37627f;
    background: #0d2032;
}

#home .eh-action-icon {
    width: 38px;
    height: 38px;
    display: grid;
    place-items: center;
    border-radius: 10px;
    background: #122d43;
    font-size: 18px;
    flex-shrink: 0;
}

#home .eh-action-card strong {
    display: block;
    font-size: 13px;
}

#home .eh-action-card small {
    display: block;
    margin-top: 4px;
    color: #8198ae;
    font-size: 10px;
}

#home .eh-action-arrow {
    margin-left: auto;
    color: #69849b;
    font-size: 18px;
}

#home .eh-activity-list {
    display: flex;
    flex-direction: column;
    gap: 9px;
}

#home .eh-activity-item {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 13px;
    padding: 14px 16px;
    border: 1px solid #1a334a;
    border-radius: 12px;
    background: #0b1928;
    color: #eaf3fb;
    text-align: left;
    cursor: pointer;
}

#home .eh-activity-item:hover {
    border-color: #345a76;
    background: #0d1e2f;
}

#home .eh-activity-status {
    font-size: 16px;
    flex-shrink: 0;
}

#home .eh-activity-main {
    flex: 1;
}

#home .eh-activity-main strong {
    display: block;
    font-size: 13px;
}

#home .eh-activity-main span {
    display: block;
    margin-top: 3px;
    color: #a9bbca;
    font-size: 11px;
}

#home .eh-activity-main small {
    display: block;
    margin-top: 3px;
    color: #71899f;
    font-size: 10px;
}

#home .eh-activity-time {
    color: #71899f;
    font-size: 10px;
    white-space: nowrap;
}

#home .eh-view-all {
    width: 100%;
    margin-top: 11px;
    padding: 12px;
    border: 1px solid #1b344b;
    border-radius: 10px;
    background: transparent;
    color: #8eb4d2;
    cursor: pointer;
    font-weight: 700;
}

#home .eh-view-all:hover {
    background: #0b1d2e;
}

#home .eh-view-all span {
    margin-left: 5px;
}

#home .eh-details-overlay {
    position: fixed;
    inset: 0;
    z-index: 1000;
    display: grid;
    place-items: center;
    padding: 20px;
    background: rgba(2, 9, 16, .78);
}

#home .eh-details-card {
    width: min(560px, 100%);
    max-height: 90vh;
    overflow-y: auto;
    position: relative;
    padding: 26px;
    border: 1px solid #31516a;
    border-radius: 18px;
    background: #0a1725;
    box-shadow: 0 20px 70px rgba(0,0,0,.45);
}

#home .eh-close-btn {
    position: absolute;
    top: 13px;
    right: 15px;
    border: 0;
    background: transparent;
    color: #91a7ba;
    font-size: 27px;
    cursor: pointer;
}

#home .eh-detail-risk {
    display: inline-block;
    padding: 5px 9px;
    border-radius: 6px;
    background: #4a2023;
    color: #ff8e91;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1px;
}

#home .eh-details-card h2 {
    margin-top: 12px;
    font-size: 22px;
}

#home .eh-detail-caller {
    margin-top: 7px;
    color: #93a9bc;
    font-size: 13px;
}

#home .eh-risk-score {
    margin-top: 22px;
}

#home .eh-risk-score > div:first-child {
    display: flex;
    justify-content: space-between;
    color: #91a7ba;
    font-size: 12px;
}

#home .eh-risk-score strong {
    color: #ff8b8e;
}

#home .eh-risk-bar {
    height: 7px;
    margin-top: 9px;
    border-radius: 20px;
    background: #1a2c3e;
    overflow: hidden;
}

#home #eh-risk-fill {
    width: 87%;
    height: 100%;
    background: #e46b70;
    border-radius: inherit;
}

#home .eh-detail-question {
    margin-top: 23px;
    margin-bottom: 10px;
    color: #e7eff7;
    font-weight: 700;
    font-size: 13px;
}

#home .eh-detail-reasons {
    display: grid;
    gap: 7px;
}

#home .eh-detail-reasons div {
    padding: 9px 11px;
    border-radius: 8px;
    background: #0e2132;
    color: #9db0c0;
    font-size: 12px;
}

#home .eh-detail-reasons div::before {
    content: "•";
    margin-right: 7px;
    color: #e7777b;
}

#home .eh-recommended {
    margin-top: 18px;
    padding: 13px;
    border: 1px solid #31475a;
    border-radius: 10px;
    background: #0d1d2c;
}

#home .eh-recommended span {
    display: block;
    color: #71899f;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
}

#home .eh-recommended strong {
    display: block;
    margin-top: 5px;
    color: #e9f2fa;
    font-size: 13px;
}

#home .eh-detail-actions {
    display: flex;
    gap: 9px;
    margin-top: 17px;
}

#home .eh-detail-actions button {
    flex: 1;
    padding: 11px;
    border: 1px solid #31516b;
    border-radius: 9px;
    background: #10283b;
    color: #e8f2fa;
    cursor: pointer;
    font-weight: 700;
}

#home .eh-detail-actions button:hover {
    background: #17374f;
}

#home .eh-detail-actions .eh-danger-btn {
    border-color: #71383b;
    background: #492225;
    color: #ffb0b2;
}

@media (max-width: 1050px) {

    #home .eh-home-header {
        flex-direction: column;
    }

    #home .eh-protection-summary {
        min-width: 0;
    }

    #home .eh-protection-grid,
    #home .eh-stat-grid,
    #home .eh-action-grid {
        grid-template-columns: repeat(2, 1fr);
    }

}

@media (max-width: 700px) {

    #home .eh-protection-summary {
        flex-wrap: wrap;
    }

    #home .eh-primary-btn {
        width: 100%;
        margin-left: 0;
    }

    #home .eh-protection-grid,
    #home .eh-stat-grid,
    #home .eh-action-grid {
        grid-template-columns: 1fr;
    }

    #home .eh-home-heading h1 {
        font-size: 27px;
    }

    #home .eh-protection-footer {
        flex-direction: column;
        gap: 7px;
    }

}
'''

# ------------------------------------------------------------
# 8. Add dedicated Home CSS before </head>
# ------------------------------------------------------------

if "id=\"echoshield-home-style\"" in html:
    print("ERROR: Home CSS already exists in clean backup.")
    print("Nothing was changed.")
    raise SystemExit(1)

style_block = (
    "\n<style id=\"echoshield-home-style\">\n"
    + home_css
    + "\n</style>\n"
)

head_close = html.lower().rfind("</head>")

if head_close == -1:
    print("ERROR: </head> not found.")
    print("Nothing was changed.")
    raise SystemExit(1)

html = html[:head_close] + style_block + html[head_close:]

# ------------------------------------------------------------
# 9. Home JavaScript
# ------------------------------------------------------------

home_js = r'''
<script id="echoshield-home-functions">
(function () {

    window.ehToggleProtectionPanel = function () {

        const panel = document.getElementById("eh-protection-panel");

        if (!panel) return;

        if (panel.style.display === "none" || panel.style.display === "") {
            panel.style.display = "block";

            setTimeout(function () {
                panel.scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });
            }, 50);

        } else {
            panel.style.display = "none";
        }
    };


    window.ehShowCallDetails = function (type) {

        const overlay = document.getElementById("eh-call-details");

        if (!overlay) return;

        const title = document.getElementById("eh-detail-title");
        const caller = document.getElementById("eh-detail-caller");
        const score = document.getElementById("eh-detail-score");
        const fill = document.getElementById("eh-risk-fill");
        const risk = document.getElementById("eh-detail-risk");

        if (type === "verified") {

            if (title) title.textContent = "Verified Caller";
            if (caller) caller.textContent = "Caller: ABC Bank";
            if (score) score.textContent = "8/100";
            if (fill) fill.style.width = "8%";

            if (risk) {
                risk.textContent = "LOW RISK";
                risk.style.background = "#173d30";
                risk.style.color = "#72dfad";
            }

        } else if (type === "suspicious") {

            if (title) title.textContent = "Suspicious Caller";
            if (caller) caller.textContent = "Caller: +91 XXXXXXX29";
            if (score) score.textContent = "61/100";
            if (fill) fill.style.width = "61%";

            if (risk) {
                risk.textContent = "MEDIUM RISK";
                risk.style.background = "#493a20";
                risk.style.color = "#f2c46d";
            }

        } else {

            if (title) title.textContent = "Potential Scam Detected";
            if (caller) caller.textContent = "Caller: +91 XXXXXXX23";
            if (score) score.textContent = "87/100";
            if (fill) fill.style.width = "87%";

            if (risk) {
                risk.textContent = "HIGH RISK";
                risk.style.background = "#4a2023";
                risk.style.color = "#ff8e91";
            }
        }

        overlay.style.display = "grid";
    };


    window.ehCloseCallDetails = function () {

        const overlay = document.getElementById("eh-call-details");

        if (overlay) {
            overlay.style.display = "none";
        }
    };


    window.ehDetailAction = function (action) {

        const messages = {
            verify: "Caller verification started",
            block: "Caller block action selected",
            report: "Report action selected"
        };

        const message = messages[action] || "Action selected";

        if (typeof window.toast === "function") {
            window.toast(message, "LOW");
        } else {
            alert(message);
        }
    };


    window.ehViewAllActivity = function () {

        if (typeof window.showPage === "function") {

            const buttons = document.querySelectorAll(
                '[data-page="calls"], #callsBtn, button[onclick*="calls"]'
            );

            let button = buttons.length ? buttons[0] : null;

            window.showPage("calls", button);
        }
    };


    window.ehOpenSecureCalls = function () {

        if (typeof window.showPage === "function") {
            window.showPage("calls");
        }
    };


    window.ehOpenVoiceScanner = function () {

        if (typeof window.showPage === "function") {
            window.showPage("scanner");
        }
    };


    window.ehCheckNumber = function () {

        const number = prompt(
            "Enter the phone number you want to check:"
        );

        if (!number) return;

        if (typeof window.toast === "function") {
            window.toast(
                "Number check requested for " + number,
                "LOW"
            );
        }
    };


    document.addEventListener("keydown", function (event) {

        if (event.key === "Escape") {
            window.ehCloseCallDetails();
        }

    });

})();
</script>
'''

# ------------------------------------------------------------
# 10. Add Home JS before </body>
# ------------------------------------------------------------

if "id=\"echoshield-home-functions\"" in html:
    print("ERROR: Home JavaScript already exists.")
    print("Nothing was changed.")
    raise SystemExit(1)

body_close = html.lower().rfind("</body>")

if body_close == -1:
    print("ERROR: </body> not found.")
    print("Nothing was changed.")
    raise SystemExit(1)

html = html[:body_close] + "\n" + home_js + "\n" + html[body_close:]

# ------------------------------------------------------------
# 11. Final safety verification
# ------------------------------------------------------------

checks = {
    "Home section": '<section id="home"' in html,
    "Home CSS": 'id="echoshield-home-style"' in html,
    "Home JS": 'id="echoshield-home-functions"' in html,
    "Live Voice": 'id="live"' in html,
    "Secure Calls": 'id="calls"' in html,
    "Voice Scanner": 'id="scanner"' in html,
    "Fraud Intelligence": 'id="fraud"' in html,
    "Security Assistant": 'id="assistant"' in html,
    "Security Reports": 'id="reports"' in html,
    "Settings": 'id="settings"' in html,
    "AASIST": "AASIST" in html,
    "WebSocket": "WebSocket" in html,
}

failed = [name for name, result in checks.items() if not result]

if failed:
    print()
    print("SAFETY CHECK FAILED.")
    print("The following were not found:")

    for item in failed:
        print("  -", item)

    print()
    print("Restoring clean backup...")

    shutil.copy2(CLEAN_BACKUP, INDEX_FILE)

    print("Original clean frontend restored.")
    raise SystemExit(1)

# ------------------------------------------------------------
# 12. Write final index.html
# ------------------------------------------------------------

INDEX_FILE.write_text(html, encoding="utf-8")

print()
print("=" * 65)
print("SUCCESS - EchoShield Home page updated safely")
print("=" * 65)

print()
print("Updated:")
print(INDEX_FILE)

print()
print("Backend:")
print("NOT MODIFIED")

print()
print("Preserved frontend features:")
print("  ✓ Live Voice")
print("  ✓ Secure Calls")
print("  ✓ Voice Scanner")
print("  ✓ AASIST")
print("  ✓ Fraud Intelligence")
print("  ✓ Security Assistant")
print("  ✓ Security Reports")
print("  ✓ Settings")
print("  ✓ WebSocket / WebRTC frontend logic")
print("  ✓ Existing frontend JavaScript")

print()
print("New Home:")
print("  ✓ Protection Status")
print("  ✓ Today's Security")
print("  ✓ Quick Actions")
print("  ✓ Recent Activity")
print("  ✓ Call Security Details")
print("  ✓ View All Activity")

print()
print("Safe backup:")
print(CLEAN_BACKUP)

print("=" * 65)