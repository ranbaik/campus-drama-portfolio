import datetime as dt
import unittest

from booking import Booking, BookingBook, BookingError

D = dt.date(2024, 4, 15)


def at(h, m=0):
    return dt.datetime.combine(D, dt.time(h, m))


class BookingRules(unittest.TestCase):
    def setUp(self):
        self.book = BookingBook()
        self.book.add(Booking("A", "kim", at(13), at(15)))

    def test_overlap_rejected(self):  # R1
        with self.assertRaises(BookingError):
            self.book.add(Booking("A", "lee", at(14), at(16)))

    def test_touching_allowed(self):  # R1 경계
        self.book.add(Booking("A", "lee", at(15), at(16)))
        self.book.add(Booking("A", "park", at(12), at(13)))
        self.assertEqual(len(self.book.bookings), 3)

    def test_other_room_ok(self):
        self.book.add(Booking("B", "lee", at(13), at(15)))

    def test_slot_and_length(self):  # R2
        with self.assertRaises(BookingError):
            self.book.add(Booking("B", "lee", at(10, 10), at(11)))
        with self.assertRaises(BookingError):
            self.book.add(Booking("B", "lee", at(9), at(12, 30)))

    def test_opening_hours(self):  # R3
        with self.assertRaises(BookingError):
            self.book.add(Booking("B", "lee", at(8, 30), at(9, 30)))

    def test_daily_limit(self):  # R4
        self.book.add(Booking("B", "kim", at(9), at(10)))
        with self.assertRaises(BookingError):
            self.book.add(Booking("C", "kim", at(16), at(17)))

    def test_suggestion(self):  # R5
        with self.assertRaises(BookingError) as ctx:
            self.book.add(Booking("A", "lee", at(14), at(15)))
        self.assertEqual(ctx.exception.suggestion, (at(15), at(16)))


if __name__ == "__main__":
    unittest.main()
