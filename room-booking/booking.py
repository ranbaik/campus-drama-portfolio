"""
강의실(세미나실) 예약 — 충돌 검사 로직 (샘플)
=============================================
포트폴리오 장면 '팀 프로젝트: 강의실 예약 웹앱'에서 내가 맡은 백엔드 핵심 로직을
강의용으로 떼어 낸 코드입니다. 웹 프레임워크 없이 순수 파이썬으로 동작합니다.

핵심 규칙 (학과 조교님 인터뷰로 정리한 요구사항 5개)
  R1. 같은 방에서 시간이 1분이라도 겹치면 예약 불가 (끝나는 시각 = 다음 시작 시각은 허용)
  R2. 예약은 30분 단위, 최소 30분 ~ 최대 3시간
  R3. 운영 시간 09:00 ~ 22:00 안에서만
  R4. 한 사람은 같은 날 최대 2건
  R5. 충돌 시 '비어 있는 가장 가까운 시간'을 추천

실행:  python booking.py        (데모)
테스트: python -m unittest test_booking.py
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

OPEN, CLOSE = dt.time(9, 0), dt.time(22, 0)
SLOT = dt.timedelta(minutes=30)
MIN_LEN, MAX_LEN = SLOT, dt.timedelta(hours=3)
MAX_PER_DAY = 2


class BookingError(ValueError):
    """예약 규칙 위반. suggestion 이 있으면 대신 가능한 시간."""

    def __init__(self, message: str, suggestion: tuple[dt.datetime, dt.datetime] | None = None):
        super().__init__(message)
        self.suggestion = suggestion


@dataclass(frozen=True)
class Booking:
    room: str
    user: str
    start: dt.datetime
    end: dt.datetime

    def overlaps(self, other: "Booking") -> bool:
        # R1: [start, end) 반열린 구간 — 끝과 시작이 맞닿는 것은 겹침이 아님
        return self.room == other.room and self.start < other.end and other.start < self.end


@dataclass
class BookingBook:
    bookings: list[Booking] = field(default_factory=list)

    def _validate_shape(self, b: Booking) -> None:
        length = b.end - b.start
        if length < MIN_LEN or length > MAX_LEN:
            raise BookingError("예약 시간은 30분 이상 3시간 이하여야 해요.")  # R2
        if length % SLOT or b.start.minute % 30 or b.start.second:
            raise BookingError("예약은 30분 단위로만 할 수 있어요.")  # R2
        if b.start.date() != b.end.date() or b.start.time() < OPEN or b.end.time() > CLOSE:
            raise BookingError("운영 시간(09:00~22:00) 안에서만 예약할 수 있어요.")  # R3

    def add(self, b: Booking) -> Booking:
        self._validate_shape(b)
        same_day = [x for x in self.bookings if x.user == b.user and x.start.date() == b.start.date()]
        if len(same_day) >= MAX_PER_DAY:
            raise BookingError(f"하루에 최대 {MAX_PER_DAY}건까지만 예약할 수 있어요.")  # R4
        clash = next((x for x in self.bookings if x.overlaps(b)), None)
        if clash:
            raise BookingError(
                f"{clash.start:%H:%M}~{clash.end:%H:%M}에 이미 예약이 있어요.",
                suggestion=self.suggest(b.room, b.start, b.end - b.start),  # R5
            )
        self.bookings.append(b)
        return b

    def suggest(self, room: str, wanted: dt.datetime, length: dt.timedelta):
        """원하는 시각에서 가장 가까운(앞뒤 모두 탐색) 빈 시간대."""
        day_open = dt.datetime.combine(wanted.date(), OPEN)
        day_close = dt.datetime.combine(wanted.date(), CLOSE)
        candidates = []
        t = day_open
        while t + length <= day_close:
            probe = Booking(room, "?", t, t + length)
            if not any(x.overlaps(probe) for x in self.bookings):
                candidates.append(t)
            t += SLOT
        if not candidates:
            return None
        best = min(candidates, key=lambda s: abs(s - wanted))
        return best, best + length


def _demo() -> None:
    d = dt.date(2024, 4, 15)
    at = lambda h, m=0: dt.datetime.combine(d, dt.time(h, m))  # noqa: E731
    book = BookingBook()
    book.add(Booking("세미나실 A", "김민수", at(13), at(15)))
    book.add(Booking("세미나실 A", "이서연", at(15), at(16)))  # 맞닿는 건 OK
    print("예약 2건 등록:", *(f"{b.user} {b.start:%H:%M}-{b.end:%H:%M}" for b in book.bookings), sep="\n  ")
    try:
        book.add(Booking("세미나실 A", "홍길동", at(14), at(15, 30)))
    except BookingError as e:
        s = e.suggestion
        print(f"\n홍길동 14:00-15:30 → 거절: {e}")
        if s:
            print(f"  추천 시간: {s[0]:%H:%M}~{s[1]:%H:%M}")


if __name__ == "__main__":
    _demo()
