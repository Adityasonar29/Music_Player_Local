# script1.py
# from services.tools.music_player.ply_yt_2 import player


"""Clean up duplicate music entries from the database."""

from db.yt_db import get_duplicate_count, remove_duplicates, remove_perticular_entry

def main():
    print("=" * 60)
    print("Music Database Duplicate Cleanup")
    print("=" * 60)
    
    # Check for duplicates
    dup_count = get_duplicate_count()
    print(f"\n📊 Duplicate entries found: {dup_count}")
    
    if dup_count == 0:
        print("✓ No duplicates! Your database is clean.")
        return
    
    # Ask user confirmation
    print(f"\nThis will remove {dup_count} duplicate entries.")
    print("(Keeps the first occurrence of each song)")
    confirm = input("\nProceed with cleanup? (yes/no): ").strip().lower()
    
    if confirm not in ['yes', 'y']:
        print("❌ Cleanup cancelled.")
        return
    
    # Remove duplicates
    print("\n🔄 Removing duplicates...")
    removed = remove_duplicates()
    
    # Verify
    remaining_dups = get_duplicate_count()
    print(f"\n✓ Successfully removed {removed} duplicate entries!")
    print(f"📊 Remaining duplicates: {remaining_dups}")
    print("\n" + "=" * 60)
    print("Cleanup complete! Your music library is now clean.")
    print("=" * 60)
