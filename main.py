from fasthtml.common import *
import random

app = FastHTML(hdrs=(picocondlink,), htmx=True)

ROWS = 1
COLS = 5
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
                P("Find the downward arrow as fast as you can.", id="instruction"),
                Button(
                    "Start Test",
                    cls="primary",
                    id="start-button",
                    **{
                        "hx-get": "/countdown",
                        "hx-target": "#grid",
                        "hx-swap": "innerHTML",
                    },
                ),
            ),
            Div(id="status"),
            Div(id="grid"),
            Div(id="result", style="margin-top:1rem;white-space:pre-line;"),
            Script(
                """
                window.select_cell = function(i){
                    if(window.clicked) return;
                    window.clicked = true;
                    let elapsed = (performance.now() - window.reactionStart)/1000;
                    htmx.ajax('GET', '/select?cell='+i+'&elapsed='+elapsed, {target:'#grid', swap:'innerHTML'});
                }
                """
            ),
        )
    )


@app.get("/countdown")
def countdown():
    reset_round()
    clear_result = Script("document.getElementById('result').innerHTML='';")
    hide_title = Script(
        "document.getElementById('title-section').style.display='none';"
        "document.getElementById('instruction').style.display='none';"
        "document.getElementById('start-button').style.display='none';"
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
        var interval = setInterval(function(){{
            counter--;
            if(counter <= 0){{
                clearInterval(interval);
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
    reset_round()
    buttons = []
    for i in range(ROWS * COLS):
        arrow = "⬇️" if i == state["target"] else "⬆️"
        buttons.append(
            Button(arrow, cls="secondary outline", **{"onclick": f"select_cell({i})"})
        )

    grid_div = Div(
        *buttons,
        id="button-grid",
        cls="grid",
        style=f"display:grid; grid-template-columns:repeat({COLS},1fr); gap:0.5rem; justify-items:center;",
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
        window.reactionStart = performance.now();
        window.clicked = false;
        if(window.timeoutHandle) clearTimeout(window.timeoutHandle);
        window.timeoutHandle = setTimeout(function(){{
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
        return Section(
            H2("🎉 Test Complete!"),
            P(f"You got {state['success']} out of {ROUNDS_TO_WIN} correct."),
            Pre(results_text),
            Div(
                Button(
                    "Restart Test",
                    cls="primary",
                    **{"hx-get": "/", "hx-target": "#grid", "hx-swap": "innerHTML"},
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
