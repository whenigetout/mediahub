import Link from 'next/link';
export default function SideNav() {
    return (
        <div className="flex h-full flex-col px-3 py-4 md:px-2">

            <form>
                <button className="flex h-12 w-full grow items-center justify-center gap-2 rounded-md bg-blue-400 p-3 text-sm font-medium hover:bg-blue-300 hover:text-blue-600 md:flex-none md:justify-start md:p-2 md:px-3 cursor-pointer">
                    Add root
                </button>
            </form>
        </div>
    );
}
