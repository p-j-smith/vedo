## Main changes

- added `plotter.pick_area()` thanks to @ZiguoAtGitHub and @RubendeBruin feedback.
- bug fix in `closest_point()` thanks to @goncalo-pt
- bug fix in tformat thanks to @JohnsWor  https://github.com/marcomusy/vedo/pull/913
- add texture to npz files thanks to @zhouzq-thu https://github.com/marcomusy/vedo/pull/918

- Fix meshlab interface thanks to @JeffreyWardman in #924
- Update `Slicer3DPlotter` thanks to @daniel-a-diaz in #925
- Improvements on `applications.Browser`
- Improvemnets on `applications.Slicer3DPlotter`


### Breaking changes
- in `plotter.add_button(func)`, must use `func(event)` instead of `func()`
(thanks to @smoothumut for spotting the bug)


-------------------------
## New/Revised Examples
```
examples/advanced/timer_callback1.py
examples/advanced/timer_callback2.py
examples/basic/buttons.py
examples/basic/input_box.py
examples/basic/sliders2.py
examples/basic/interaction_modes2.py
examples/volumetric/slicer1.py
```

### Broken Examples
```
```



