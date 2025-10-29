// tracevault/frontend/tailwind.config.js

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        'primary-dark': '#1a202c', // Dark blue/gray for background
        'accent-blue': '#4c51bf',  // Deep blue for buttons/highlights
        'secondary-light': '#a0aec0', // Light gray for text
        'success-green': '#38a169',
        'error-red': '#e53e3e',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
