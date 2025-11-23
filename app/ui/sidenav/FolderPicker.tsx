// FolderPicker.tsx (improved)
// "use client" required because we use browser APIs and hooks
"use client";

import React, { useRef, useState } from "react";
import { useRouter } from "next/navigation";

export default function FolderPicker({ initialSelected }: { initialSelected?: string }) {
    const [selected, setSelected] = useState<string | null>(initialSelected ?? null);
    const fileInputRef = useRef<HTMLInputElement | null>(null);
    const router = useRouter();

    // Called when the hidden input returns files (webkitdirectory fallback)
    function onFilesSelected(e: React.ChangeEvent<HTMLInputElement>) {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        // webkitRelativePath example: "my-folder/sub/file.txt"
        const first = files[0] as File & { webkitRelativePath?: string };
        const rel = (first as any).webkitRelativePath || first.name;
        const root = rel.includes("/") ? rel.split("/")[0] : rel;
        setSelected(root);

        // reset so picking same folder twice will still trigger change
        e.currentTarget.value = "";

        // tell Next to refresh server components that might rely on server state
        router.refresh();
    }

    // Try modern picker -> fallback to hidden input
    async function handlePickFolder() {
        const win = window as any;
        if (typeof win.showDirectoryPicker === "function") {
            try {
                // showDirectoryPicker returns a handle to the selected folder
                const dirHandle: any = await win.showDirectoryPicker();
                const name = dirHandle?.name ?? "Unnamed folder";
                setSelected(name);
                router.refresh(); // refresh server-side data if needed
            } catch (err) {
                // user cancelled, ignore
            }
            return;
        }

        // fallback: open hidden input which has webkitdirectory attribute
        fileInputRef.current?.click();
    }

    return (
        <div>
            {/* Button (visible) — change text to 'Select folder' if you prefer */}
            <button
                type="button"
                onClick={handlePickFolder}
                className="flex h-12 grow items-center justify-center gap-2 rounded-md bg-blue-400 p-3 text-sm font-medium hover:bg-blue-300 hover:text-blue-600 md:flex-none md:justify-start md:p-2 md:px-3 cursor-pointer"
            >
                Select folder
            </button>

            {/* Hidden input fallback for older browsers.
          It returns File objects for files inside the folder (webkitdirectory),
          so we infer the folder name from webkitRelativePath. */}
            <input
                ref={fileInputRef}
                type="file"
                // non-standard attributes — fine in practice
                // @ts-ignore
                webkitdirectory=""
                // @ts-ignore
                directory=""
                multiple
                onChange={onFilesSelected}
                style={{ display: "none" }}
            />

            <div className="mt-4">
                <strong>Selected folder:</strong>
                <div className="mt-2 p-2 w-1/2 rounded bg-gray-50 text-sm">
                    <span className="text-gray-500">{selected ?? "No folder selected"}</span>
                </div>
            </div>
        </div>
    );
}
