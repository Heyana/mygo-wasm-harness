//go:build js && wasm

package main

import (
	"runtime"
	"syscall/js"
)

// init exposes Go heap stats to the benchmark driver as window.__gomem().
func init() {
	js.Global().Set("__gomem", js.FuncOf(func(this js.Value, args []js.Value) any {
		var m runtime.MemStats
		runtime.ReadMemStats(&m)
		return map[string]any{
			"heapAllocMB": float64(m.HeapAlloc) / 1048576,
			"heapSysMB":   float64(m.HeapSys) / 1048576,
			"sysMB":       float64(m.Sys) / 1048576,
		}
	}))
}
