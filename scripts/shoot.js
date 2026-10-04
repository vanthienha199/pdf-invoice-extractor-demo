// Render the gallery HTML inputs to PNG at 2x. Run after scripts/gallery.py.
//   npm i playwright && npx playwright install chromium
const { chromium } = require("playwright");
const path = require("path");
const RAW = path.resolve(__dirname, "../../raw");
const OUT = path.resolve(__dirname, "../out");

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 2 });

  const summary = await ctx.newPage();
  await summary.goto("file://" + path.join(OUT, "summary.html"), { waitUntil: "networkidle" });
  await summary.waitForTimeout(1500);
  await summary.screenshot({ path: path.join(RAW, "summary_dark.png") });
  console.log("summary_dark.png");

  for (const [name, w, h] of [["terminal", 1180, 540], ["tests", 1020, 760]]) {
    const p = await ctx.newPage();
    await p.setViewportSize({ width: w, height: h });
    await p.goto("file://" + path.join(RAW, `${name}.html`), { waitUntil: "networkidle" });
    await p.waitForTimeout(1200);
    const card = await p.locator(".card").boundingBox();
    await p.screenshot({ path: path.join(RAW, `${name}.png`), clip: card });
    console.log(`${name}.png`);
    await p.close();
  }

  await ctx.close();
  await browser.close();
})();
