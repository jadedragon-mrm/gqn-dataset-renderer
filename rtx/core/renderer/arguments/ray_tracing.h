#pragma once

namespace rtx {
class RayTracingArguments {
private:
    int _num_rays_per_pixel;
    int _max_bounce;
public:
    RayTracingArguments();
    int num_rays_per_pixel();
    void set_num_rays_per_pixel(int num);
    int max_bounce();
    void set_max_bounce(int bounce);
};
}