// tracevault/frontend/next.config.js

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Use the 'src' directory for pages and components
  experimental: {
    appDir: true,
  },
  output: 'standalone', // Optimized build output for Docker/deployment
};

module.exports = nextConfig;
