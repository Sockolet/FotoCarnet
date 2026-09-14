import unittest
from dataclasses import replace
from math import nan

from fotocarnet.layout import Corner, Margins, Settings, crop_rect, make_layout


class LayoutTests(unittest.TestCase):
    def test_defaults_have_real_sizes_and_leave_the_rest_blank(self):
        layout = make_layout(Settings())
        self.assertEqual(layout.page_count, 1)
        self.assertEqual(len(layout.positions(0)), 6)
        self.assertEqual(layout.positions(0)[0].x, 5)
        self.assertEqual(layout.positions(0)[0].y, 5)
        for photo in layout.positions(0):
            self.assertEqual((photo.width, photo.height), (26, 32))
            self.assertLessEqual(photo.x + photo.width, 87)
            self.assertLessEqual(photo.y + photo.height, 71)

    def test_one_photo_is_anchored_to_each_corner(self):
        expected = {
            Corner.TOP_LEFT: (5, 5),
            Corner.TOP_RIGHT: (179, 5),
            Corner.BOTTOM_LEFT: (5, 260),
            Corner.BOTTOM_RIGHT: (179, 260),
        }
        for corner, coordinates in expected.items():
            with self.subTest(corner=corner):
                photo = make_layout(Settings(copies=1, corner=corner)).positions(0)[0]
                self.assertEqual((photo.x, photo.y), coordinates)

    def test_hardware_margins_are_respected_on_all_sides(self):
        margins = Margins(9, 12, 17, 20)
        for corner in Corner:
            layout = make_layout(Settings(corner=corner), minimum_margins=margins)
            for photo in layout.positions(0):
                self.assertGreaterEqual(photo.x, 9)
                self.assertGreaterEqual(photo.y, 12)
                self.assertLessEqual(photo.x + photo.width, 193)
                self.assertLessEqual(photo.y + photo.height, 277)

    def test_overflow_keeps_exact_number_and_size(self):
        layout = make_layout(Settings(copies=120))
        self.assertEqual(layout.capacity, 56)
        self.assertEqual(layout.page_count, 3)
        self.assertEqual([len(layout.positions(p)) for p in range(3)], [56, 56, 8])
        for page in range(3):
            self.assertTrue(all((p.width, p.height) == (26, 32) for p in layout.positions(page)))

    def test_last_page_is_also_anchored(self):
        layout = make_layout(Settings(copies=57, corner=Corner.BOTTOM_RIGHT))
        self.assertEqual(len(layout.positions(1)), 1)
        self.assertEqual((layout.positions(1)[0].x, layout.positions(1)[0].y), (179, 260))

    def test_compact_block_does_not_use_a_nearly_empty_full_width_row(self):
        layout = make_layout(Settings(copies=8))
        photos = layout.positions(0)
        width = max(p.x + p.width for p in photos) - min(p.x for p in photos)
        height = max(p.y + p.height for p in photos) - min(p.y for p in photos)
        self.assertEqual((width, height), (110, 66))

    def test_no_overlap_or_overflow_for_sizes_counts_and_corners(self):
        for width, height in ((26, 32), (35, 45), (50.8, 50.8), (100, 150)):
            for count in (1, 2, 8, 17, 57, 121):
                for corner in Corner:
                    with self.subTest(size=(width, height), count=count, corner=corner):
                        layout = make_layout(Settings(width, height, count, corner))
                        self.assertEqual(sum(len(layout.positions(p)) for p in range(layout.page_count)), count)
                        for page in range(layout.page_count):
                            photos = layout.positions(page)
                            for index, photo in enumerate(photos):
                                self.assertGreaterEqual(photo.x, 5 - 1e-8)
                                self.assertGreaterEqual(photo.y, 5 - 1e-8)
                                self.assertLessEqual(photo.x + width, 205 + 1e-8)
                                self.assertLessEqual(photo.y + height, 292 + 1e-8)
                                for other in photos[index + 1:]:
                                    self.assertTrue(
                                        photo.x + width <= other.x or other.x + width <= photo.x
                                        or photo.y + height <= other.y or other.y + height <= photo.y
                                    )

    def test_landscape_and_exact_fit(self):
        layout = make_layout(Settings(width=297, height=210, copies=2, margin=0, gap=0), (297, 210))
        self.assertEqual(layout.capacity, 1)
        self.assertEqual(layout.page_count, 2)
        self.assertEqual((layout.positions(0)[0].x, layout.positions(0)[0].y), (0, 0))

    def test_invalid_inputs_fail_explicitly(self):
        for changes in (
            {"width": 0}, {"height": nan}, {"width": 300}, {"copies": 0},
            {"copies": 1.5}, {"copies": True}, {"margin": -1}, {"gap": -1},
            {"margin": 200}, {"corner": "middle"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                make_layout(replace(Settings(), **changes))
        with self.assertRaises(ValueError):
            make_layout(Settings()).positions(1)


class CropTests(unittest.TestCase):
    def test_crop_preserves_photo_aspect_ratio(self):
        for dimensions in ((1000, 400), (400, 1000), (260, 320)):
            crop = crop_rect(*dimensions, 26, 32)
            self.assertAlmostEqual(crop.width / crop.height, 26 / 32)
            self.assertGreaterEqual(crop.x, 0)
            self.assertGreaterEqual(crop.y, 0)
            self.assertLessEqual(crop.x + crop.width, dimensions[0])
            self.assertLessEqual(crop.y + crop.height, dimensions[1])

    def test_focus_reaches_edges_and_zoom_does_not_stretch(self):
        left = crop_rect(1000, 400, 26, 32, (0, 0), 2)
        right = crop_rect(1000, 400, 26, 32, (1, 1), 2)
        self.assertEqual((left.x, left.y), (0, 0))
        self.assertEqual(right.x + right.width, 1000)
        self.assertEqual(right.y + right.height, 400)
        self.assertEqual(left.width / left.height, 26 / 32)

    def test_invalid_crop_fails(self):
        with self.assertRaises(ValueError):
            crop_rect(0, 100, 26, 32)
        with self.assertRaises(ValueError):
            crop_rect(100, 100, 26, 32, zoom=0.5)


if __name__ == "__main__":
    unittest.main()
