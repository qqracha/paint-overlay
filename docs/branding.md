# Branding

Name: Paint Overlay. Logo: a translucent cyan glass palette and graphite fountain pen. The reference was supplied by the application owner; the delivered asset is a newly generated illustration, not a copy of the reference.

Generated with the built-in ImageGen tool. App ICO is a multi-resolution format conversion of the PNG; its alpha channel is preserved.

Prompt:

> Use case: logo-brand. Create a new Windows application icon for Paint Overlay, using the supplied old Paint icon only as a conceptual reference. Replace the paintbrush with a beautiful graphite navy fountain pen with a silver nib, angled lower-left to upper-right. Redesign the palette into a modern translucent frosted glass cyan rounded palette with three luminous coral, yellow and teal paint dots and a subtle second offset glass outline suggesting an overlay window. Polished restrained 3D desktop icon, bold readable silhouette at 32 pixels, no text, no letters, no watermark. Genuine transparent background, centered square, generous 8% margin. Distinct new composition rather than tracing original.

The ribbon uses Qt painting and application-owned icon drawing code. No screenshot or Microsoft executable/resource file is bundled.

## Glass material

The glass appearance is inspired by [Apple HIG Materials](https://developer.apple.com/design/human-interface-guidelines/materials). This is not Apple's native Liquid Glass runtime. On Windows 11, the application requests [DWMSBT_TRANSIENTWINDOW / Desktop Acrylic](https://learn.microsoft.com/en-us/windows/win32/api/dwmapi/ne-dwmapi-dwm_systembackdrop_type), paints translucent gradients and specular edges, and renders icons directly with QPainter. Older Windows versions use a translucent fallback. No backdrop screenshot is cached or exported by the glass effect.

The non-activating HUD prefers Windows composition blur with custom translucent glass tint. Desktop Acrylic is retained as a fallback. Geometry reveal animation avoids layered-window opacity, which can force an opaque backdrop on tool windows. The glass was visually checked over a synthetic colored background; the background in docs/glass-demo.png contains no user desktop content.

Version 2.1 removes the cursor-following radial highlight. The visible glass outline follows the native rounded window corners; the redundant internal rim and title area are removed. Toolbar icons use thin vector strokes. Screenshot exports target the monitor of the last drawing operation and never include HUD controls.

Version 2.1.1 enlarges the ribbon and its labels. Capture uses temporary [WDA_EXCLUDEFROMCAPTURE](https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-setwindowdisplayaffinity), hides all visible application top-level widgets, and flushes DWM before sampling the screen. A native test verified that the saved HUD region, including its surrounding shadow margin, matches an unobstructed background byte-for-byte. Toast text is painted directly instead of relying on transparent child-label composition.
