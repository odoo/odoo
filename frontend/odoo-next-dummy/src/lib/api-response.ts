import { NextResponse } from "next/server";

export function jsonOk<T>(data: T, status = 200) {
  return NextResponse.json(data, { status });
}

export function jsonError(message: string, status = 500, details?: unknown) {
  return NextResponse.json(
    {
      error: message,
      details: details ?? null
    },
    { status }
  );
}
