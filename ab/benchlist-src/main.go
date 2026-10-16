// benchlist is the A/B workload: a virtual list of 500 rows of text,
// scrolled continuously by scripted wheel events. Identical source builds
// on both routes (fork Canvas2D and upstream WebGL2); only the module
// (and thus the backend) differs.
package main

import (
	"fmt"
	"log"

	"github.com/egoist/mygo"
	"github.com/egoist/mygo/ui"
)

type bench struct {
	list ui.ListState
}

// sentences is a pool of realistic, varied-length lines; row i shows
// sentences[i%len(sentences)] so text layout/shaping is real work and
// deterministic across routes.
var sentences = []string{
	"The quick brown fox jumps over the lazy dog near the riverbank.",
	"Performance is a feature, and every millisecond counts on low-end hardware.",
	"Go compiles to WebAssembly with a single command and no toolchain drama.",
	"Virtualized lists only build the rows you can actually see on screen.",
	"Text shaping runs once per unique string and caches by width.",
	"Damage tracking uploads just the dirty rectangles to the GPU.",
	"A mutex that is not re-entrant will deadlock the goroutine that holds it.",
	"Measure first, then optimize; never the other way around.",
	"The canvas 2D context draws the frame the UI package rasterized.",
	"WebGL2 moves the same pixels through shaders on the graphics processor.",
	"Twelve hundred lines of layout code, each one earning its place.",
	"Scroll velocity decays with friction, then snaps to the nearest row.",
	"Every frame has a budget: sixteen milliseconds at sixty hertz.",
	"Zero allocations on the hot path keeps the garbage collector quiet.",
	"Retain the subtree, skip the rebuild, present the damage.",
	"Fonts are measured once; glyphs are cached until the atlas fills.",
	"Headless Chromium with SwiftShader stands in for a GPU here.",
	"The compositor waits for no one, least of all a slow main thread.",
	"Deterministic workloads make for honest benchmarks.",
	"Row four hundred and ninety-nine is the last one you will scroll to.",
	"Concurrency is not parallelism, but both beat waiting on the network.",
	"Backpressure propagates from the slowest stage of the pipeline.",
	"Cache invalidation remains one of the two hard problems.",
	"A benchmark that cannot be reproduced is just an anecdote.",
}

func rowText(i int) string {
	return fmt.Sprintf("Row %d — %s", i, sentences[i%len(sentences)])
}

func (b *bench) view(c *ui.Context) {
	t := c.Theme()
	ui.List(c, &b.list, 500, func(i int) {
		row := ui.Row(c).Height(46).PaddingX(12).Gap(10).Center()
		if i%2 == 0 {
			row.Background(t.Surface)
		}
		row.Children(func() {
			ui.Textf(c, "%d", i).FontSize(12).Width(44).TextColor(t.TextMuted)
			ui.Text(c, rowText(i)).FontSize(14).Grow(1)
		})
	}).Fill()
}

func main() {
	b := &bench{}
	mygo.App.WhenReady(func() {
		mygo.NewWindow(mygo.WindowOptions{
			Title:   "BenchList",
			Width:   1280,
			Height:  800,
			Content: ui.View(b.view),
		})
	})
	if err := mygo.App.Run(); err != nil {
		log.Fatal(err)
	}
}
