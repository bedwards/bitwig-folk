"""Folk Sequence CLI — unified command-line tool for the Bitwig YouTube pipeline."""

import argparse
import sys


def cmd_transcode(args):
    """Transcode source .mov to YouTube-optimized .mp4."""
    from folkseq.transcode import transcode
    transcode(args.input, output=args.output, dry_run=args.dry_run)


def cmd_thumbnail(args):
    """Generate thumbnail using Gemini image generation."""
    from folkseq.thumbnail import generate_thumbnail
    generate_thumbnail(args.episode, candidates=args.candidates)


def cmd_upload(args):
    """Upload video to YouTube with metadata and thumbnail."""
    from folkseq.upload import upload
    upload(args.episode, schedule=args.schedule)


def cmd_schedule(args):
    """Schedule next N videos for daily upload at 7:30 AM Central."""
    from folkseq.schedule import schedule_videos
    schedule_videos(start=args.start, days=args.days)


def cmd_status(args):
    """Show pipeline status for all videos."""
    from folkseq.status import show_status
    show_status()


def cmd_channel(args):
    """Generate/update channel metadata assets."""
    from folkseq.channel import generate_assets
    generate_assets(asset_type=args.type)


def cmd_auth(args):
    """Authenticate with YouTube (OAuth 2.0 flow)."""
    from folkseq.auth import authenticate
    authenticate()


def cmd_doctor(args):
    """Verify all required tools and credentials are available."""
    from folkseq.doctor import check_all
    check_all()


def main():
    parser = argparse.ArgumentParser(
        prog="folkseq",
        description="Folk Sequence — Bitwig YouTube Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  folkseq transcode "Folk Sequence 001.mov"
  folkseq thumbnail 001
  folkseq upload 001
  folkseq schedule --days 7
  folkseq status
  folkseq channel --type banner
  folkseq auth
  folkseq doctor
""",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # transcode
    p = subparsers.add_parser("transcode", help="Transcode .mov to YouTube .mp4")
    p.add_argument("input", help="Path to source .mov file")
    p.add_argument("-o", "--output", help="Output .mp4 path (default: auto)")
    p.add_argument("-n", "--dry-run", action="store_true", help="Print ffmpeg command without running")
    p.set_defaults(func=cmd_transcode)

    # thumbnail
    p = subparsers.add_parser("thumbnail", help="Generate thumbnail with Gemini")
    p.add_argument("episode", help="Episode number (e.g., 000)")
    p.add_argument("-c", "--candidates", type=int, default=3, help="Number of candidates to generate (default: 3)")
    p.set_defaults(func=cmd_thumbnail)

    # upload
    p = subparsers.add_parser("upload", help="Upload video to YouTube")
    p.add_argument("episode", help="Episode number (e.g., 000)")
    p.add_argument("-s", "--schedule", help="Publish datetime (ISO 8601) or 'next' for next available slot")
    p.set_defaults(func=cmd_upload)

    # schedule
    p = subparsers.add_parser("schedule", help="Schedule batch of uploads")
    p.add_argument("--start", help="First episode to schedule (default: next unscheduled)")
    p.add_argument("--days", type=int, default=7, help="Number of days to schedule (default: 7)")
    p.set_defaults(func=cmd_schedule)

    # status
    p = subparsers.add_parser("status", help="Show pipeline status")
    p.set_defaults(func=cmd_status)

    # channel
    p = subparsers.add_parser("channel", help="Generate channel assets")
    p.add_argument("--type", choices=["profile", "banner", "all"], default="all", help="Asset type to generate")
    p.set_defaults(func=cmd_channel)

    # auth
    p = subparsers.add_parser("auth", help="Authenticate with YouTube")
    p.set_defaults(func=cmd_auth)

    # doctor
    p = subparsers.add_parser("doctor", help="Verify tools and credentials")
    p.set_defaults(func=cmd_doctor)

    args = parser.parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
