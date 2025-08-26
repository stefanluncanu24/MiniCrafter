#!/usr/bin/env python3
"""Easy launcher for Mini Crafter GUI modes."""

import sys
import os
import subprocess
import datetime

def main():
    print("🎮 Mini Crafter GUI Launcher")
    print("=" * 40)
    print()
    
    print("Choose your Mini Crafter mode:")
    print("1. MDP Mode (9×9 world, fully observable, peaceful)")
    print("2. POMDP Mode (15×15 world, partially observable, peaceful)")
    # print("3. MDP Mode with monsters (9×9 world, fully observable)")
    # print("4. POMDP Mode with monsters (15×15 world, partially observable)")
    # print("5. Custom configuration")
    print()
    
    try:
        choice = input("Enter your choice (1-2): ").strip()
        
        cmd_args = {}
        if choice == '1':
            cmd_args = {'mode': 'mdp', 'peaceful': 'True'}
            print("Selected: MDP Mode (9×9, fully observable, peaceful)")
        elif choice == '2':
            cmd_args = {'mode': 'pomdp', 'peaceful': 'True'}
            print("Selected: POMDP Mode (15×15, partially observable, peaceful)")
        # elif choice == '3':
        #     cmd_args = {'mode': 'mdp', 'peaceful': 'False'}
        #     print("Selected: MDP Mode (9×9, fully observable, with monsters)")
        # elif choice == '4':
        #     cmd_args = {'mode': 'pomdp', 'peaceful': 'False'}
        #     print("Selected: POMDP Mode (15×15, partially observable, with monsters)")
        # elif choice == '5':
        #     print("\nCustom Configuration:")
        #     mode = input("Mode (mdp/pomdp) [mdp]: ").strip() or 'mdp'
        #     peaceful = input("Peaceful mode (True/False) [True]: ").strip() or 'True'
        #     worldgen = input("Worldgen module [mini_crafter.worldgen]: ").strip() or 'mini_crafter.worldgen'
        #     cmd_args = {'mode': mode, 'peaceful': peaceful}
        #     if worldgen != 'mini_crafter.worldgen':
        #         cmd_args['worldgen'] = worldgen
        else:
            print("Invalid choice. Exiting.")
            return

        # # Ask for layout if mode is MDP
        # if cmd_args.get('mode') == 'mdp':
        #     print()
        #     layout = input("Choose layout for MDP (default/full) [default]: ").strip().lower() or 'default'
        #     if layout == 'full':
        #         cmd_args['layout'] = 'full'

        # Ask about recording
        print()
        record_choice = input("Do you want to record this gameplay session? (y/n) [n]: ").strip().lower()
        if record_choice == 'y':
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            default_dir = f"records/{cmd_args['mode']}_{cmd_args['peaceful']}_{timestamp}"
            record_dir = input(f"Enter directory to save recording [{default_dir}]: ").strip() or default_dir
            cmd_args['record'] = record_dir

        # Build command
        cmd = [sys.executable, '-m', 'mini_crafter.run_gui']
        for k, v in cmd_args.items():
            cmd.extend([f'--{k}', v])
        
        print()
        print("=" * 40)
        print("🎮 Controls:")
        print("  WASD - Move")
        print("  SPACE - Interact/Do")
        print("  TAB - Sleep")
        print("  R/T/F/P - Place stone/table/furnace/plant")
        print("  1-6 - Craft tools and weapons")
        print("  ESC - Quit")
        print("=" * 40)
        print()
        print(f"Starting game with command: {' '.join(cmd)}")
        print()
        
        # Run the GUI
        subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
        
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"An error occurred: {e}")
        print("\nMake sure you have pygame installed ('pip install pygame') and the environment is set up correctly.")


if __name__ == '__main__':
    main()

