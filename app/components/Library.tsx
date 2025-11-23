import { _FASTAPI_BACKEND_BASE_URL } from "@/app/lib/config";

const Library = async () => {
    const url = `${_FASTAPI_BACKEND_BASE_URL}/library`;

    // call the FastAPI endpoint
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) {
        return <div>⚠️ Couldn’t fetch data — backend returned an error ({res.status}).</div>;
    }

    const data = await res.json();

    // concise destructuring
    const { library, roots = [] } = data;
    const root_folders = roots.map((root: { path: string }) => root.path);
    console.log("roots", root_folders);

    return (
        <div>
            <div>Library: {library.name}</div>
            <ul>
                {root_folders.map((path: string, i: number) => (
                    <li key={i}>{path}</li>
                ))}
            </ul>
        </div>
    )
}

export default Library