"""
Author: Josh Spisak <jspisak@andrew.cmu.edu>
Date: 8/26/2021
Description: a simple utility to parse command line arguments
"""

class Arguments():
    positional_args = []
    flags = []
    set_flags = {}

    def __init__(self, arg_flags = []):
        # What arguments to look for that will be set
        self.arg_flags = arg_flags
        # Argument values
        self.positional_args = []
        self.boolean_flags = []
        self.set_flags = {}
        # Arguments after a `--` that should be processed later
        self.post_args = []

    # def flag_to_config(self, flag_name, config_key):
    #     """
    #     Used to export arguments to the central config
    #     """
    #     v = self.get_flag_value(flag_name)
    #     if v is not None:
    #         jdc.set_config("cli", config_key, v)
    #     if self.get_flag_boolean(flag_name):
    #         jdc.set_config("cli", config_key, True)

    def get_arg_count(self):
        return len(self.positional_args)

    def get_arg_at(self, idx, default=None):
        """
        Gets a positional arg
        """
        if idx >= len(self.positional_args):
            return default
        return self.positional_args[idx]

    def get_flag_value(self, flag, default = None):
        """
        Gets the value of a set flag
        """
        if type(flag) is list:
            for f in flag:
                if f in self.set_flags:
                    return self.set_flags[f]
        else:
            if flag in self.set_flags:
                return self.set_flags[flag]
        return default

    def get_flag_boolean(self, flag):
        """
        Returns true if a flag was passed, false if not
        """
        if type(flag) is list:
            for f in flag:
                if f in self.boolean_flags:
                    return True
        else:
            if flag in self.boolean_flags:
                return True
        return False

    def parse_arguments(self, arguments):
        """
        Parses arguments from command line
        """
        idx = 0
        # Process each argument
        while idx < len(arguments):
            arg = arguments[idx]
            next_arg = None
            ## Terminate at an alone -- and treat the rest as post_args
            if arg == "--" and len(arg) == 2:
                self.postpost_args = arguments[idx + 1:]
                break
            if idx + 1 < len(arguments):
                next_arg = arguments[idx + 1]
                if next_arg == "--" and len(next_arg) == 2:
                    next_arg = None

            # Process an argument that has a - (a set or flag arg)
            def process_set(arg_t):
                # If there is an equal then it is a set argument
                if "=" in arg_t:
                    split_arg = arg_t.split("=")
                    self.set_flags[split_arg[0]] = split_arg[1]
                    return 0
                # If it is in arg_flags then we can expect the next arg to be the set argument
                elif arg_t in self.arg_flags:
                    if next_arg is None:
                        raise Exception("Excpected argument to flag {}".format(arg_t))
                    self.set_flags[arg_t] = next_arg
                    return 1
                # Else it's just a flag
                self.boolean_flags.append(arg_t)
                return 0

            # Handle set / flag args
            if arg[:2] == "--":
                idx += process_set(arg[2:])
            elif arg[0] == "-":
                idx += process_set(arg[1:])
            # Else it's just a position arg!
            else:
                self.positional_args.append(arg)
            idx = idx + 1

