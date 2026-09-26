# VectorFreed

## Abstract

This document introduces "VectorFreed", a vulnerability chain that begins with a use-after-free I (@rafabd1) found in librsvg ([CVE-2026-96889](https://www.cve.org/CVERecord?id=CVE-2026-96889)). In a Node.js/Sharp/libvips build, this bug led to command execution. It covers the bug, the paths confirmed in applications so far, and the fixes available now.

## Details

An SVG can include another SVG through XInclude. In the vulnerable path, librsvg starts parsing an included document while libxml2 is still expanding an entity in the outer one. If the included SVG declares an entity with the same name, librsvg replaces and frees the first entity. libxml2 still holds a pointer to it.

When the included parse ends, libxml2 carries on with that old pointer. The memory may already belong to something else by then, so later writes can corrupt it. A crash is one result. In other cases, this also led to command execution.

## Where it shows up

The attacker needs crafted SVG markup to reach librsvg. That can happen when an application accepts an SVG file, but it can also happen when the application builds an SVG from user input. Merely using librsvg somewhere in the dependency tree does not establish an exploitable path; the input has to reach an affected build when the image is rendered.

The Next.js route we tested accepted text instead of an SVG upload. It placed that text inside an inline SVG for the Node.js version of `ImageResponse`. A [separate escaping bug in Satori](https://github.com/vercel/satori/security/advisories/GHSA-wx4j-mvgx-mqwp) let the text change the generated SVG markup. Sharp/libvips then passed that SVG to librsvg. Vercel tracked the Next.js path as [CVE-2026-94545](https://github.com/vercel/next.js/security/advisories/GHSA-vcvr-r3jv-pc5j). The Edge version of `ImageResponse` is not affected by this path. Here is a short [Next.js reproduction](https://x.com/rafabd1_/status/2102459649924727213).

## Scope

During this research, I identified affected input paths in multiple downstream products and confirmed command execution in several of them, including the Next.js case described above. How that input reaches librsvg varies from product to product. That is why an upstream image parser bug can turn up in places that do not seem related at first; the recent [libheif case](https://vercel.com/blog/reproducing-disclosing-and-fixing-the-libheif-vulnerability-with-hacktron-and-the-maintainers) is another example. It does not mean every product using librsvg is remotely exploitable.

## What to update

- **librsvg:** 2.63.2 has the fix, with backports in 2.62.4 and [2.61.5](https://gitlab.gnome.org/GNOME/librsvg/-/tags/2.61.5). If you use an older vendor build, check whether it includes the fix. See the [librsvg advisory](https://rustsec.org/advisories/RUSTSEC-2026-0305.html).
- **Next.js:** Versions 16.2.0 through 16.3.5 are affected when an application puts attacker-controlled values into SVG content, attributes, or styles on the Node.js `ImageResponse` path. Upgrade to 16.3.6.
- **Satori:** If you use it directly, 0.33.5 fixes the separate escaping bug used in the Next.js route.

If you use Sharp's prebuilt binaries, check the `@img/sharp-libvips-*` package your app installed. It [bundles libvips and its dependencies](https://github.com/lovell/sharp-libvips), including [librsvg](https://github.com/lovell/sharp-libvips/blob/main/THIRD-PARTY-NOTICES.md). Updating the system copy of librsvg may leave your app using the old one.

## PoCs and what comes next

The [UAF PoC](pocs/README.md) includes an SVG generator for several input paths and can be used to check the use-after-free at the start of the chain.

So far, I haven't found a public exploit that takes this chain all the way from crafted SVG to command execution. The bug and patches are already public, though, and with current AI tools it's fairly easy to work back to the full chain from them. Given that, treat the exploit as if it were already public and update affected dependencies or mitigate the input path as soon as possible.

> [!WARNING]
> There is no universal RCE PoC for this chain; the payload needs to be adjusted for each target. Most public "PoCs" I've seen so far don't reproduce the actual RCE chain. Some rely on SVG `<foreignObject>` for the claimed execution, which is not the exploit path described here.

For initial validation, the UAF PoC is more practical. I plan to publish an RCE PoC for the Next.js case (CVE-2026-94545) in a separate repository. I'll also publish the technical write-up in the coming weeks, with the steps from the UAF to command execution and a post-mortem covering this past month of research into the chain.

## References

- [librsvg issue and fix](https://gitlab.gnome.org/GNOME/librsvg/-/work_items/1241)
- [librsvg RustSec advisory](https://rustsec.org/advisories/RUSTSEC-2026-0305.html)
- [Next.js security update](https://nextjs.org/blog/nextjs-security-update-september-22-2026) and [Next.js advisory](https://github.com/vercel/next.js/security/advisories/GHSA-vcvr-r3jv-pc5j)
- [Satori advisory](https://github.com/vercel/satori/security/advisories/GHSA-wx4j-mvgx-mqwp)
- [Next.js reproduction post](https://x.com/rafabd1_/status/2102459649924727213)
