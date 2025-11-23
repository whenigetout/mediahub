// components/FolderBrowser.tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type Entry = {
    name: string;
    path: string;
    is_dir: boolean;
    filesize?: number | null;
    mtime?: number | null;
};

export default function FolderBrowser({
    initial = "/",
}: {
    initial?: string;
}) {
    const [current, setCurrent] = useState<string>(initial);
    const [entries, setEntries] = useState<Entry[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const router = useRouter();

    useEffect(() => {
        loadDir(current);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    async function loadDir(path: string) {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch("/api/fs", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path, include_files: false, max_entries: 1000 }),
            });
            const json = await res.json();
            if (!res.ok) {
                throw new Error(json.detail || json.error || JSON.stringify(json));
            }
            setEntries(json.entries ?? []);
            setCurrent(path);
        } catch (err: any) {
            console.error("loadDir error:", err);
            setError(String(err));
        } finally {
            setLoading(false);
        }
    }

    async function openDir(path: string) {
        await loadDir(path);
    }

    async function addRoot(path: string) {
        if (!confirm(`Add folder as root?\n\n${path}`)) return;
        try {
            const res = await fetch("/api/add_root", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path }),
            });
            const json = await res.json();
            if (!res.ok) {
                throw new Error(json.detail || json.error || JSON.stringify(json));
            }
            // Successful — refresh server components that render library if any
            router.refresh();
            alert("Added root: " + path);
        } catch (err: any) {
            console.error("addRoot error:", err);
            alert("Failed to add root: " + (err.message || String(err)));
        }
    }

    function upOne() {
        try {
            const p = new URL(current, "file://"); // trick to use URL for path operations? keep simple:
        } catch { }
        // naive up logic:
        const segments = current.split("/").filter(Boolean);
        if (current.startsWith("/") && segments.length === 0) return; // at root
        if (segments.length <= 1) {
            loadDir(current.startsWith("/") ? "/" : ".");
            return;
        }
        const parent = current.startsWith("/") ? "/" + segments.slice(0, -1).join("/") : segments.slice(0, -1).join("/");
        loadDir(parent);
    }

    return (
        <div className="p-2">
            <div className="flex items-center gap-2 mb-2">
                <button
                    onClick={() => loadDir("/")}
                    className="rounded bg-gray-500 px-2 py-1 text-sm"
                >
                    Root
                </button>
                <button
                    onClick={upOne}
                    className="rounded bg-gray-500 px-2 py-1 text-sm"
                >
                    Up
                </button>
                <div className="ml-auto text-xs text-gray-500">Current: {current}</div>
            </div>

            {loading && <div className="text-sm text-gray-500">Loading…</div>}
            {error && <div className="text-sm text-red-500">{error}</div>}

            <ul className="divide-y">
                {entries.length === 0 && !loading && (
                    <li className="py-2 text-sm text-gray-500">No folders found</li>
                )}
                {entries.map((e, i) => (
                    <li key={e.path + i} className="py-2 flex items-center gap-3">
                        {e.is_dir ? (
                            <button
                                onClick={() => openDir(e.path)}
                                className="px-2 py-1 rounded bg-blue-50 text-blue-700 text-sm"
                            >
                                Open
                            </button>
                        ) : (
                            <div style={{ width: 64 }} />
                        )}

                        <div style={{ flex: 1 }}>
                            <div className="text-sm font-medium">{e.name}</div>
                            <div className="text-xs text-gray-500">{e.path}</div>
                        </div>

                        {e.is_dir && (
                            <button
                                onClick={() => addRoot(e.path)}
                                className="px-2 py-1 rounded bg-green-500 text-white text-sm"
                            >
                                Add as root
                            </button>
                        )}
                    </li>
                ))}
            </ul>
        </div>
    );
}
