Vendored so the resume checker never calls a CDN:
- pdfjs-dist-6.3.289 (legacy build), Apache-2.0, https://github.com/mozilla/pdf.js
- mammoth-1.13.0 (mammoth.browser.min.js), BSD-2-Clause, https://github.com/mwilliamson/mammoth.js
Loaded only from this site; the page's Content-Security-Policy sets connect-src 'none'.
