// app/api/fs/route.ts
import { NextResponse } from "next/server";
import { _FASTAPI_BACKEND_BASE_URL } from "@/app/lib/config";

export async function POST(req: Request) {
    try {
        const body = await req.json();

        const res = await fetch(`${_FASTAPI_BACKEND_BASE_URL.replace(/\/+$/, "")}/library/list_dir`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });

        const contentType = res.headers.get("content-type") ?? "";
        const data = contentType.includes("application/json") ? await res.json() : await res.text();

        return NextResponse.json(data, { status: res.status });
    } catch (err: any) {
        console.error("proxy /api/fs error:", err);
        return NextResponse.json({ ok: false, error: String(err) }, { status: 500 });
    }
}
