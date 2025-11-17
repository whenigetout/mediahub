import { _FASTAPI_BACKEND_BASE_URL } from "@/app/lib/config";
import LibraryPanel from "@/app/components/LibraryPanel";

const Page = async () => {
  try {

    async function updateUI() {
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

      console.log("logging data", count);

      return (
        <div>
          <h1>Welcome to Mediahub!</h1>
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
        </div>
      );
    }

    async function pollRoots() {
      const url = `${_FASTAPI_BACKEND_BASE_URL}/library/root_folders`;
      const res = await fetch(url);
      const { roots } = await res.json();
      // update your UI using roots[].status
      const allIdle = roots.length > 0 && roots.every((r: any) => r.status === "idle");
      setTimeout(pollRoots, 3000); // poll every 3s
      if (allIdle) {
        return await updateUI();
      } else {
        return (
          <div>
            <h1>Welcome to Mediahub!</h1>
            <div>⚙️ Library still scanning or not ready yet.</div>
          </div>
        );
      }


    }
    return await pollRoots();

  }
  catch (error) {
    return (
      <div>
        <h1>Welcome to Mediahub!</h1>
        <div>❌ Can’t fetch data — backend server may be offline.</div>
      </div>
    );
  }

};

export default Page