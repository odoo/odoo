import csv
import os
import sys
from datetime import datetime
import anthropic

# 1. تهيئة ملف CSV للتسجيل
CSV_FILE = "scratch_api_calls.csv"
FIELDNAMES = [
    "timestamp",
    "call_type",
    "model",
    "request_id",
    "input_tokens",
    "output_tokens",
    "stop_reason",
    "status",
]


def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def log_call(
    call_type,
    model,
    request_id,
    input_tokens,
    output_tokens,
    stop_reason,
    status="SUCCESS",
):
    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(
            {
                "timestamp": datetime.now().isoformat(),
                "call_type": call_type,
                "model": model,
                "request_id": request_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "stop_reason": stop_reason,
                "status": status,
            }
        )


def run_benchmarks():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable is missing.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    target_model = "claude-opus-4-8"

    init_csv()
    print(f"=== Starting Scratch Benchmarks for model: {target_model} ===")

    # ------------------------------------------------------------------
    # 1. Plain Call
    # ------------------------------------------------------------------
    print("\n[1/4] Executing Plain Call...")
    try:
        response = client.messages.create(
            model=target_model,
            max_tokens=150,
            messages=[
                {
                    "role": "user",
                    "content": "Extract total amount: Invoice total is $450.00 USD",
                }
            ],
        )
        req_id = getattr(response, "_request_id", "N/A")
        log_call(
            call_type="plain_call",
            model=target_model,
            request_id=req_id,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            stop_reason=response.stop_reason,
        )
        print(
            f"  -> Success | Request ID: {req_id} | Usage: In={response.usage.input_tokens}, Out={response.usage.output_tokens}"
        )
    except Exception as e:
        print(f"  -> Plain Call Failed: {e}")

    # ------------------------------------------------------------------
    # 2. System Prompt Call
    # ------------------------------------------------------------------
    print("\n[2/4] Executing Call with system= prompt...")
    try:
        response = client.messages.create(
            model=target_model,
            max_tokens=150,
            system="You are a strict JSON extraction engine. Respond with raw JSON only.",
            messages=[
                {"role": "user", "content": "Vendor: Acme Corp, Date: 2026-08-01"}
            ],
        )
        req_id = getattr(response, "_request_id", "N/A")
        log_call(
            call_type="system_prompt_call",
            model=target_model,
            request_id=req_id,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            stop_reason=response.stop_reason,
        )
        print(
            f"  -> Success | Request ID: {req_id} | Usage: In={response.usage.input_tokens}, Out={response.usage.output_tokens}"
        )
    except Exception as e:
        print(f"  -> System Prompt Call Failed: {e}")

    # ------------------------------------------------------------------
    # 3. Streaming Call closed by get_final_message()
    # ------------------------------------------------------------------
    print("\n[3/4] Executing client.messages.stream() with get_final_message()...")
    try:
        with client.messages.stream(
            model=target_model,
            max_tokens=150,
            system="You are an invoice parser assistant.",
            messages=[
                {
                    "role": "user",
                    "content": "Summarize invoice status: Line 1 item desk $200",
                }
            ],
        ) as stream:
            for text in stream.text_stream:
                pass  # Consume stream tokens

            final_message = stream.get_final_message()

        req_id = getattr(final_message, "_request_id", "N/A")
        log_call(
            call_type="streaming_call",
            model=target_model,
            request_id=req_id,
            input_tokens=final_message.usage.input_tokens,
            output_tokens=final_message.usage.output_tokens,
            stop_reason=final_message.stop_reason,
        )
        print(
            f"  -> Success | Request ID: {req_id} | Final Usage: In={final_message.usage.input_tokens}, Out={final_message.usage.output_tokens}"
        )
    except Exception as e:
        print(f"  -> Streaming Call Failed: {e}")

    # ------------------------------------------------------------------
    # 4. Count Tokens Call
    # ------------------------------------------------------------------
    print("\n[4/4] Executing client.messages.count_tokens()...")
    try:
        token_count = client.messages.count_tokens(
            model=target_model,
            system="You are a strict JSON extraction engine.",
            messages=[
                {
                    "role": "user",
                    "content": "Calculate token consumption pre-flight for invoice ingestion.",
                }
            ],
        )
        req_id = getattr(token_count, "_request_id", "N/A")
        # count_tokens لا يولد output_tokens
        log_call(
            call_type="count_tokens",
            model=target_model,
            request_id=req_id,
            input_tokens=token_count.input_tokens,
            output_tokens=0,
            stop_reason="count_only",
        )
        print(
            f"  -> Success | Request ID: {req_id} | Calculated Input Tokens: {token_count.input_tokens}"
        )
    except Exception as e:
        print(f"  -> Count Tokens Failed: {e}")

    print(f"\n=== Benchmark Complete. Results appended to '{CSV_FILE}' ===")


if __name__ == "__main__":
    run_benchmarks()
