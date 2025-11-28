# Make sure your backend venv is active
# Make sure your Docker (Qdrant) is running

from backend.app.graph import math_agent
from rich.console import Console
from rich.syntax import Syntax
import warnings

# Suppress all warnings
warnings.filterwarnings("ignore")

console = Console()

def run_test(question):
    console.print(f"\n[bold yellow]Testing question:[/bold yellow] {question}")
    inputs = {"question": question}
    
    final_state = {}
    try:
        # We will stream all events for logging
        for event in math_agent.stream(inputs):
            for key, value in event.items():
                console.print(f"[bold cyan]Node:[/bold cyan] {key}")
                console.print(f"[bold green]State Change:[/bold green]\n{value}\n")
                # The __end__ event contains the final, complete state
                if key == "__end__":
                    final_state = value
                    break
                else:
                    # Merge the state changes into our final_state
                    final_state.update(value)

    except Exception as e:
        console.print(f"[bold red]An error occurred:[/bold red] {e}")
        return

    console.print("\n[bold magenta]--- FINAL RESULT ---[/bold magenta]")
    
    # This is the final state after the graph has finished
    if not final_state:
        console.print("[bold red]Graph did not run.[/bold red]")
        return
    if final_state.get("error"):
        console.print(f"[bold red]Error:[/bold red] {final_state['error']}")
    elif final_state.get("solution"):
        syntax = Syntax(final_state.get('solution'), "markdown", theme="monokai", line_numbers=True)
        console.print(syntax)
        console.print(f"[bold blue]Source:[/bold blue] {final_state.get('source')}")
    else:
        # This will catch any other final state that is not an error or solution
        console.print("[bold yellow]Graph finished, but no solution or error was in the final state.[/bold yellow]")
        
# 1. Test a non-math question (should be rejected by input guardrail)
run_test("What is the capital of France?")

# 2. Test a PII question (should be rejected by input guardrail)
run_test("My SSN is 123-45-678, can you solve x+1=2?")

# 3. Test a KB question (This will now work!)
#    This question is in your database, so it should be fast and use 'kb' source.
run_test("The value of the integral $\int_{0}^{1} \sqrt{\frac{1-x}{1+x}} dx$ is...")

# 4. Test a general math question (should trigger web search)
run_test("How do I solve the quadratic equation $ax^2 + bx + c = 0$?")

# 5. Test another web search
run_test("What is the derivative of $x^3 \sin(x)$?")