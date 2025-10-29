// tracevault/frontend/src/app/layout.js

import { Inter } from 'next/font/google';
import './../styles/globals.css';

// Configure the Inter font (used in tailwind.config.js)
const inter = Inter({ subsets: ['latin'] });

export const metadata = {
  title: 'TraceVault - Evidence Analysis System',
  description: 'AI-Powered Digital Evidence and OSINT Analysis.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <main className="min-h-screen flex flex-col">
          {children}
        </main>
      </body>
    </html>
  );
}
