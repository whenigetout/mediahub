// app/api/add_root/route.ts
import { NextResponse } from "next/server";

import { _FASTAPI_BACKEND_BASE_URL } from "@/app/lib/config";

export async function POST(req: Request) {
    try {
        const body = await req.json(); // expect { path: string, label?: string }

        // Forward the request to FastAPI. Adjust URL if your FastAPI expects query params.
        const url = `${_FASTAPI_BACKEND_BASE_URL.replace(/\/+$/, "")}/library/add_root_folder?path=${encodeURIComponent(body.path)}`;
        const res = await fetch(url, { method: "POST" });

        const contentType = res.headers.get("content-type") ?? "";
        const data = contentType.includes("application/json") ? await res.json() : await res.text();

        return NextResponse.json(data, { status: res.status });
    } catch (err: any) {
        console.error("proxy /api/add_root error:", err);
        return NextResponse.json({ ok: false, error: String(err) }, { status: 500 });
    }
}
