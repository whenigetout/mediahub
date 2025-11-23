import { _FASTAPI_BACKEND_BASE_URL } from "../lib/config";

const FilesList = async () => {
    const url = `${_FASTAPI_BACKEND_BASE_URL}/library/files`;

    // call the FastAPI endpoint
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) {
        return <div>⚠️ Couldn’t fetch data — backend returned an error ({res.status}).</div>;
    }

    const data = await res.json();

    // concise destructuring
    const { count = 0, files = [] } = data;
    const paths = files.map((f: { path: string }) => f.path);
    const filenames = files.map((f: { filename: string }) => f.filename);

    // console.log("logging data", count);
    return (
        <div>
            The output is: <br />
            {count} files found. File names below:
            <br />
            <ul className="mt-2 space-y-1 text-sm text-gray-300">
                {filenames.map((path: string, i: number) => (
                    <li key={i}>{path}</li>
                ))}
            </ul>
        </div>
    )
}

export default FilesList