from fasthtml.common import *
import random

app = FastHTML(hdrs=(picolink), htmx=True, debug=True)

ROWS = 4
COLS = 10
TIME_LIMIT = 2.0
ROUNDS_TO_WIN = 5
COUNTDOWN = 5
COOLDOWN = 2000  # ms

state = {
    "round": 0,
    "success": 0,
    "target": None,
    "start_time": None,
    "last_result": "",
    "results": [],
}


def reset_round():
    state["target"] = random.randint(0, ROWS * COLS - 1)
    state["start_time"] = None
    state["last_result"] = ""


def reset_game():
    state["round"] = 0
    state["success"] = 0
    state["results"] = []
    reset_round()


@app.get("/")
def index():
    reset_game()
    return Main(
        Div(
            Header(H1("Reaction Speed Test", cls="contrast"), id="title-section"),
            Section(
                H2("Settings"),
                Form(
                    Label("Rows"),
                    Input(type="number", name="rows", value=ROWS, min=1, required=True),
                    Label("Columns"),
                    Input(type="number", name="cols", value=COLS, min=1, required=True),
                    Label("Time Limit (seconds)"),
                    Input(
                        type="number",
                        step="0.1",
                        name="time_limit",
                        value=TIME_LIMIT,
                        min=0.5,
                        required=True,
                    ),
                    Label("Rounds to Win"),
                    Input(
                        type="number",
                        name="rounds",
                        value=ROUNDS_TO_WIN,
                        min=1,
                        required=True,
                    ),
                    Label("Countdown Before Start (seconds)"),
                    Input(
                        type="number",
                        name="countdown",
                        value=COUNTDOWN,
                        min=0,
                        required=True,
                    ),
                    Label("Cooldown Between Rounds (ms)"),
                    Input(
                        type="number",
                        name="cooldown",
                        value=COOLDOWN,
                        min=0,
                        required=True,
                    ),
                    Button(
                        "Save & Start Test",
                        cls="primary",
                        type="submit",
                        **{
                            "hx-post": "/configure",
                            "hx-target": "#grid",
                            "hx-swap": "innerHTML",
                        },
                    ),
                ),
                id="settings",
            ),
            Div(id="status"),
            Div(id="grid"),
            Div(id="result", style="margin-top:1rem;white-space:pre-line;"),
            # <-- important: make select_cell available globally so onclick handlers work
            Script(
                """
                window.select_cell = function(i){
                    if(window.clicked) return;
                    window.clicked = true;
                    if(window.timeoutHandle) { clearTimeout(window.timeoutHandle); window.timeoutHandle = undefined; }
                    let elapsed = (performance.now() - (window.reactionStart || performance.now()))/1000;
                    // send elapsed to server
                    htmx.ajax('GET', '/select?cell='+i+'&elapsed='+elapsed, {target:'#grid', swap:'innerHTML'});
                }
                """
            ),
        ),
        cls="container",
    )


@app.post("/configure")
def configure(
    rows: int, cols: int, time_limit: float, rounds: int, countdown: int, cooldown: int
):
    global ROWS, COLS, TIME_LIMIT, ROUNDS_TO_WIN, COUNTDOWN, COOLDOWN
    ROWS = int(rows)
    COLS = int(cols)
    TIME_LIMIT = float(time_limit)
    ROUNDS_TO_WIN = int(rounds)
    COUNTDOWN = int(countdown)
    COOLDOWN = int(cooldown)

    reset_game()

    # Hide settings/title immediately when starting from the settings form, then start countdown.
    hide_settings = Script(
        "var s=document.getElementById('settings'); if(s) s.style.display='none';"
        "var t=document.getElementById('title-section'); if(t) t.style.display='none';"
        "var instr=document.getElementById('instruction'); if(instr) instr.style.display='none';"
        "var sb=document.getElementById('start-button'); if(sb) sb.style.display='none';"
    )
    return Section(hide_settings, countdown_route())


@app.get("/countdown")
def countdown_route():
    # Prepare a new target for the upcoming round
    reset_round()

    clear_result = Script("document.getElementById('result').innerHTML='';")
    # Ensure settings/title are hidden when countdown appears (useful when countdown is triggered mid-session)
    hide_title = Script(
        "var s=document.getElementById('settings'); if(s) s.style.display='none';"
        "var t=document.getElementById('title-section'); if(t) t.style.display='none';"
        "var instr=document.getElementById('instruction'); if(instr) instr.style.display='none';"
        "var sb=document.getElementById('start-button'); if(sb) sb.style.display='none';"
    )
    countdown_div = Div(
        f"Starting in {COUNTDOWN}...",
        id="countdown",
        style="font-size:2rem;text-align:center;margin:1rem",
    )
    js = Script(
        f"""
        var counter = {COUNTDOWN};
        var countdownElem = document.getElementById('countdown');
        // show initial value immediately
        countdownElem.innerText = 'Starting in ' + counter + '...';
        var interval = setInterval(function(){{
            counter--;
            if(counter <= 0){{
                clearInterval(interval);
                // start the round (replace #grid with the start view)
                htmx.ajax('GET', '/start', {{target:'#grid', swap:'innerHTML'}});
                countdownElem.remove();
            }} else {{
                countdownElem.innerText = 'Starting in ' + counter + '...';
            }}
        }}, 1000);
        """
    )
    return Section(clear_result, hide_title, countdown_div, js)


@app.get("/start")
def start():
    # choose a new target at round start
    reset_round()
    buttons = []
    for i in range(ROWS * COLS):
        arrow = "⬇️" if i == state["target"] else "⬆️"
        buttons.append(
            Button(
                arrow,
                style="padding: 0;font-size: 4em;margin: 0;border: 0; background: none;",
                **{"onclick": f"select_cell({i})"},
            )
        )

    grid_div = Div(
        *buttons,
        id="button-grid",
        cls="grid",
        style=f"display:grid; grid-template-columns:repeat({COLS},1fr); gap:0.2rem; justify-items:center;",
    )
    status = P(
        f"Round {state['round']+1} of {ROUNDS_TO_WIN} · Success: {state['success']}",
        id="status",
    )
    result_div = Div(
        state["last_result"],
        id="result",
        style="margin-top:1rem;white-space:pre-line;",
    )

    js = Script(
        f"""
        // start timing for this round
        window.reactionStart = performance.now();
        window.clicked = false;
        if(window.timeoutHandle) clearTimeout(window.timeoutHandle);
        window.timeoutHandle = setTimeout(function(){{
            // timeout => act like the user selected -1
            window.select_cell(-1);
        }}, {int(TIME_LIMIT*1000)});
        """
    )
    return Section(status, grid_div, result_div, js)


def next_round_script():
    return Script(
        f"""
        setTimeout(function(){{
            htmx.ajax('GET','/countdown',{{target:'#grid', swap:'innerHTML'}});
        }},{COOLDOWN});
        """
    )


@app.get("/select")
def select(cell: int, elapsed: float):
    cell = int(cell)
    elapsed = float(elapsed)
    sec = int(elapsed)
    ms = int((elapsed - sec) * 1000)
    readable = f"{sec}.{ms:03d} seconds"

    if cell == state["target"]:
        result = f"✅ Correct! Reaction time: {readable}"
        state["success"] += 1
    elif cell == -1:
        result = f"⏰ Timeout! Reaction time: {readable}"
    else:
        result = f"❌ Wrong! Reaction time: {readable}"

    state["round"] += 1
    state["last_result"] = result
    state["results"].append(result)

    if state["round"] >= ROUNDS_TO_WIN:
        results_text = "\n".join(state["results"])
        # reload page on restart so settings reappear cleanly
        return Section(
            H2("🎉 Test Complete!"),
            P(f"You got {state['success']} out of {ROUNDS_TO_WIN} correct."),
            P(f"Total fails: {ROUNDS_TO_WIN - state['success']}."),
            Pre(results_text),
            Div(
                Button(
                    "Restart Test",
                    cls="primary",
                    **{"onclick": "window.location.href='/'"},
                )
            ),
        )

    # Show only last result and schedule next round
    result_div = Div(
        state["last_result"],
        id="result",
        style="margin-top:1rem;white-space:pre-line;",
    )
    return Section(result_div, next_round_script())


if __name__ == "__main__":
    serve()
