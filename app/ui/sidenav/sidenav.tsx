import Link from 'next/link';
import Library from '../../components/Library';
import FolderPicker from './FolderPicker';
import FolderBrowser from '@/app/components/FolderBrowser';

export default function SideNav() {
    return (
        <div className="flex h-full flex-col px-3 py-4 md:px-2">

            {/* <FolderPicker /> */}
            <FolderBrowser />
            <Library />
        </div>
    );
}
