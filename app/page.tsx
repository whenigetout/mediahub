import { _FASTAPI_BACKEND_BASE_URL } from "@/app/lib/config";
import LibraryPanel from "@/app/components/LibraryPanel";
import LayoutSeparatorTemp from "./ui/LayoutSeparatorTemp";
import FilesList from "./components/FilesList";
import SideNav from "./ui/sidenav/sidenav";

const Page = async () => {
  try {

    async function updateUI() {

      return (
        <div>
          <LayoutSeparatorTemp />
          <h1>Welcome to Mediahub!</h1>
          <FilesList />
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