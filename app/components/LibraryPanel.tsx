"use client";

import { useEffect, useRef, useState } from "react";
import { _FASTAPI_BACKEND_BASE_URL } from "@/app/lib/config";

type Root = { id: string; path: string; label: string; status: string; updated_at?: string };
type MediaFile = { id: string; path: string; filename?: string };

const ROOTS_URL = `${_FASTAPI_BACKEND_BASE_URL}/library/root_folders`; // change if your endpoint is different
const FILES_URL = `${_FASTAPI_BACKEND_BASE_URL}/library/files`;

export default function LibraryPanel() {
    const [roots, setRoots] = useState<Root[] | null>(null);
    const [files, setFiles] = useState<MediaFile[] | null>(null);
    const [error, setError] = useState<string | null>(null);
    const pollingRef = useRef<number | null>(null);

    async function fetchRoots(): Promise<Root[]> {
        try {
            const res = await fetch(ROOTS_URL, { cache: "no-store" });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const json = await res.json();
            // if your API returns { roots: [...] } adapt accordingly
            const list: Root[] = Array.isArray(json.roots) ? json.roots : (json as Root[]);
            setRoots(list);
            setError(null);
            return list;
        } catch (e: any) {
            console.error("fetchRoots error", e);
            setError("Could not fetch root folders");
            setRoots([]);
            return [];
        }
    }

    async function fetchFiles() {
        try {
            const res = await fetch(`${FILES_URL}?limit=1000`, { cache: "no-store" });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const json = await res.json();
            setFiles(json.files ?? []);
            setError(null);
        } catch (e: any) {
            console.error("fetchFiles error", e);
            setError("Could not fetch files");
            setFiles([]);
        }
    }

    useEffect(() => {
        let cancelled = false;
        let fastInterval = 3000; // poll interval while scanning
        let consecutiveFailures = 0;

        // core polling function
        const doPoll = async () => {
            if (cancelled) return;
            const currentRoots = await fetchRoots();
            if (cancelled) return;

            // consider empty roots as "not ready" (your choice)
            const allIdle = currentRoots.length > 0 && currentRoots.every(r => r.status === "idle");

            if (allIdle) {
                // stop fast polling and fetch file list once
                if (pollingRef.current) {
                    clearInterval(pollingRef.current);
                    pollingRef.current = null;
                }
                await fetchFiles();

                // switch to a slow heartbeat to detect later external changes
                pollingRef.current = window.setInterval(doPoll, 30000); // 30s heartbeat
                return;
            }

            // still scanning: ensure a fast poll interval is running
            if (!pollingRef.current) {
                pollingRef.current = window.setInterval(doPoll, fastInterval);
            }
        };

        // start immediately
        doPoll().catch(e => console.error("initial poll failed", e));

        return () => {
            cancelled = true;
            if (pollingRef.current) {
                clearInterval(pollingRef.current);
                pollingRef.current = null;
            }
        };
    }, []); // empty deps => run once on mount

    // UI states
    if (error) {
        return (
            <div>
                <h1>Welcome to Mediahub!</h1>
                <div className="text-red-400">{error}</div>
                <div>
                    <button onClick={() => { setError(null); void fetchRoots(); }}>Retry</button>
                </div>
            </div>
        );
    }

    if (!roots) return <div>Loading library status…</div>;

    if (roots.length === 0) {
        return (
            <div>
                <h1>Welcome to Mediahub!</h1>
                <div>⚙️ Library not configured — no root folders added.</div>
            </div>
        );
    }

    // if files are not yet loaded, it means roots exist but not idle yet
    if (!files) {
        // show a small summary of root statuses
        return (
            <div>
                <h1>Welcome to Mediahub!</h1>
                <div>⚙️ Library is scanning. Root statuses:</div>
                <ul>
                    {roots.map(r => <li key={r.id}>{r.label ?? r.path} — {r.status}</li>)}
                </ul>
            </div>
        );
    }

    // files loaded — show them
    return (
        <div>
            <h1>Welcome to Mediahub!</h1>
            <div>{files.length} files</div>
            <ul>
                {files.map(f => <li key={f.id}>{f.path}</li>)}
            </ul>
        </div>
    );
}
